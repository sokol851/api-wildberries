from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from aiogram.filters import Command

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from sqlalchemy.future import select
from decouple import config

from app.db import async_session
from app.models import Product


class Form(StatesGroup):
    artikul = State()


bot = Bot(token=config('TELEGRAM_TOKEN'))
dp = Dispatcher()

# Кнопка
button = KeyboardButton(text="Получить данные по товару")
markup = ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True)


@dp.message(Command(commands=["start"]))
async def start(message: types.Message):
    """ Приветствие """
    await message.answer(
        "Добро пожаловать! Нажмите кнопку ниже для получения данных по товару.",
        reply_markup=markup
    )


@dp.message(F.text)
async def request_artikul(message: types.Message, state: FSMContext):
    """ Получение артикула """
    await message.answer("Пожалуйста, введите артикул товара:")
    await state.set_state(Form.artikul)


@dp.message(Form.artikul)
async def send_product_data(message: types.Message, state: FSMContext):
    artikul = message.text

    async with async_session() as session:
        result = await session.execute(
            select(Product).where(Product.artikul == artikul)
        )
        product = result.scalars().first()

        if product:
            await message.answer(
                f"**Название:** {product.name}\n"
                f"**Артикул:** {product.artikul}\n"
                f"**Цена:** {product.price} руб.\n"
                f"**Рейтинг:** {product.rating}\n"
                f"**Количество на складах:** {product.total_quantity}",
                parse_mode="Markdown"
            )
        else:
            await message.answer("Товар не найден в базе данных.")
    await state.clear()


async def start_bot(app):
    await dp.start_polling(bot)
