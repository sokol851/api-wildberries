from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import (ContentType, KeyboardButton, Message,
                           ReplyKeyboardMarkup)
from decouple import config
from sqlalchemy.future import select

from app.db import async_session
from app.models import Product
from app.services import fetch_product_from_api


class Form(StatesGroup):
    artikul = State()


bot = Bot(token=config('TELEGRAM_TOKEN'))
dp = Dispatcher()

# Кнопка
button = KeyboardButton(text="Получить данные по товару")
markup = ReplyKeyboardMarkup(keyboard=[[button]],
                             resize_keyboard=True)


@dp.message(Command(commands=["start"]))
async def start(message: Message):
    """ Приветствие """
    await message.answer(
        "Добро пожаловать! Нажмите кнопку ниже "
        "для получения данных по товару.",
        reply_markup=markup
    )


@dp.message(F.content_type == ContentType.TEXT, StateFilter(None))
async def request_artikul(message: Message, state: FSMContext):
    """ Получение артикула """
    if message.text != "Получить данные по товару":
        await message.answer("Выберите действие из меню")
    else:
        await state.set_state(Form.artikul)
        await message.answer("Пожалуйста, введите артикул товара:")


@dp.message(Form.artikul)
async def send_product_data(message: Message, state: FSMContext):
    """ Проверка существования артикула на WB """
    artikul = message.text.strip()

    async with async_session() as session:
        # Ищет продукт в базе данных
        result = await session.execute(
            select(Product).where(Product.artikul == artikul)
        )
        product = result.scalars().first()

        if not product:
            # Если нет, обращаемся к WB
            await message.answer("Товар не найден в базе."
                                 " Пытаюсь получить данные из"
                                 " внешнего источника...")
            product_data = await fetch_product_from_api(artikul)

            if product_data:
                # Добавляем новый продукт в базу
                product = Product(**product_data)
                session.add(product)
                try:
                    await session.commit()
                    await session.refresh(product)
                    await message.answer("Товар успешно добавлен"
                                         " в базу данных.")
                except Exception:
                    await session.rollback()
                    await message.answer("Произошла ошибка при добавлении"
                                         " товара в базу данных.")
                    await state.clear()
                    return
            else:
                await message.answer("Не удалось найти артикул.")
                await state.clear()
                return

        # Вывод информации о продукте
        await message.answer(
            f"**Название:** {product.name}\n"
            f"**Артикул:** {product.artikul}\n"
            f"**Цена:** {product.price} руб.\n"
            f"**Рейтинг:** {product.rating}\n"
            f"**Количество на складах:** {product.total_quantity}",
            parse_mode="Markdown"
        )

    await state.clear()


async def start_bot(app):
    await dp.start_polling(bot)
