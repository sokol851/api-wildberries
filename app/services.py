import logging

import httpx
from sqlalchemy.future import select

from app.db import async_session
from app.models import Product

logger = logging.getLogger(__name__)


async def update_product_data(artikul: str):
    """ Обновление данных товара """
    logger.info(f"Начало обновления данных для артикула {artikul}")
    async with httpx.AsyncClient() as client:
        url = (f"https://card.wb.ru/cards/v1/detail?"
               f"appType=1&curr=rub&dest=-1257786&spp=30&nm={artikul}")

        response = await client.get(url)

    if response.status_code != 200:
        logger.error(f"Ошибка получения товара {artikul}:"
                     f" {response.status_code}")
        return

    data = response.json()

    async with async_session() as session:

        try:
            product_data = data['data']['products'][0]

            result = await session.execute(
                select(Product).where(Product.artikul == artikul)
            )

            product = result.scalars().first()

            if product:
                product.name = product_data['name']
                product.price = product_data['salePriceU'] / 100
                product.rating = product_data.get('rating', 0)
                product.total_quantity = product_data['totalQuantity']
                await session.commit()
                logger.info(f"Данные {artikul} обновлены")
            else:
                logger.warning(f"Артикул {artikul} не найден в базе данных.")
        except (IndexError, KeyError) as e:
            logger.exception(f"Ошибка обновления артикула {artikul}: {e}")


async def fetch_product_from_api(artikul: str):
    """ Проверка существования артикула """
    url = (
        f"https://card.wb.ru/cards/v1/detail?"
        f"appType=1&curr=rub&dest=-1257786&spp=30&nm={artikul}"
    )
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    try:
        product_data = data['data']['products'][0]
        return {
            'artikul': artikul,
            'name': product_data['name'],
            'price': product_data['salePriceU'] / 100,
            'rating': product_data.get('rating', 0),
            'total_quantity': product_data['totalQuantity']
        }
    except (IndexError, KeyError):
        return None
