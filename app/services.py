import httpx
from sqlalchemy.future import select

from app.db import async_session
from app.models import Product


async def update_product_data(artikul: str):
    """ Обновление данных товара """
    async with httpx.AsyncClient() as client:

        url = (f"https://card.wb.ru/cards/v1/detail?"
               f"appType=1&curr=rub&dest=-1257786&spp=30&nm={artikul}")

        response = await client.get(url)

    if response.status_code != 200:
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

        except (IndexError, KeyError):
            pass
