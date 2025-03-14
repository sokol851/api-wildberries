import asyncio
import logging

import httpx
from fastapi import Depends, FastAPI, HTTPException, responses, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.baerer import verify_token
from app.bot import bot, start_bot
from app.db import async_session, engine
from app.models import Base, Product
from app.schemas import JobsBase, ProductBase, ProductCreate
from app.services import update_product_data
from app.sheduler import scheduler

app = FastAPI(
    title='API для взаимодействия с WB',
    version="1.0.0"
)

logger = logging.getLogger(__name__)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


@app.on_event("startup")
async def startup():
    """ При запуске """
    # Создание таблиц для артикулов
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Запуск бота
    asyncio.create_task(start_bot(app))


@app.on_event("shutdown")
async def on_shutdown():
    """ При завершении """
    # Остановка бота
    await bot.close()


@app.post("/api/v1/products",
          response_model=ProductBase,
          dependencies=[Depends(verify_token)],
          summary='Добавление артикула',
          tags=['Работа с товаром'])
async def create_product(
        product_in: ProductCreate,
        session: AsyncSession = Depends(get_session)):
    """ Добавление товара """

    # Проверка, существует ли уже товар с таким артикулом
    result = await session.execute(
        select(Product).where(Product.artikul == product_in.artikul)
    )
    existing_product = result.scalars().first()
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Этот артикул уже есть в базе"
        )

    # Продолжаем, если новый
    url = (f"https://card.wb.ru/cards/v1/detail?appType=1&"
           f"curr=rub&dest=-1257786&spp=30&nm={product_in.artikul}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=400,
                            detail="Ошибка при получении данных с Wildberries")

    data = response.json()
    try:
        # Добавляем в базу, если успешно
        product_data = data['data']['products'][0]

        product = Product(
            artikul=product_in.artikul,
            name=product_data['name'],
            price=product_data['salePriceU'] / 100,
            rating=product_data.get('rating', 0),
            total_quantity=product_data['totalQuantity']
        )

        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product

    except (IndexError, KeyError):
        raise HTTPException(status_code=404,
                            detail="Товар не найден")


@app.get("/api/v1/subscribe/{artikul}",
         dependencies=[Depends(verify_token)],
         summary='Подписка на артикул',
         tags=['Работа с товаром'])
async def subscribe_product(artikul: str):
    """ Подписка на обновление товара """

    # Проверка, существует ли уже задача с данным артикулом
    job_id = f"update_{artikul}"
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        logger.info(f"Попытка повторной подписки на артикул {artikul}")
        return responses.JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": f"Подписка на артикул {artikul} уже оформлена"}
        )

    scheduler.add_job(
        func=update_product_data,
        trigger='interval',
        args=[artikul],
        minutes=30,
        id=f"update_{artikul}",
        replace_existing=True
    )
    logger.info(f"Подписка на артикул {artikul} оформлена")
    return {"message": f"Подписка на артикул {artikul} оформлена"}


@app.get("/api/v1/subscribe",
         response_model=JobsBase,
         dependencies=[Depends(verify_token)],
         summary='Получение списка задач',
         tags=['Работа с товаром'])
async def list_jobs():
    """ Список всех подписок в планировщике """
    jobs = scheduler.get_jobs()
    jobs_info = [
        {
            "id": job.id,
            "Следующее время обновления": job.next_run_time.isoformat() if
            job.next_run_time else None,
            "Интервал": str(job.trigger),
            "Артикула": job.args
        }
        for job in jobs
    ]
    return responses.JSONResponse(content={"jobs": jobs_info})
