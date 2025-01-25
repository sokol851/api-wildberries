import logging
import asyncio

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db import async_session, engine
from app.models import Base, Product
from app.schemas import ProductBase, ProductCreate
from app.services import update_product_data
from app.sheduler import scheduler
from app.bot import start_bot, bot

app = FastAPI()

logger = logging.getLogger(__name__)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(start_bot(app))


@app.on_event("shutdown")
async def on_shutdown():
    await bot.close()


@app.post("/api/v1/products", response_model=ProductBase)
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


@app.get("/api/v1/subscribe/{artikul}")
async def subscribe_product(artikul: str):
    """ Подписка на обновление товара """
    scheduler.add_job(
        func=update_product_data,
        trigger='interval',
        args=[artikul],
        minutes=30,
        id=f"update_{artikul}",
        replace_existing=True
    )
    return {"message": f"Подписка на артикул {artikul} оформлена"}
