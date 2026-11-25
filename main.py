import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

import database  # Подключаем наш файл базы данных
load_dotenv()
# Токен лучше хранить в переменной окружения BOT_TOKEN
TOKEN = os.getenv("BOT_TOKEN")
   

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Инициализируем БД при старте
database.init_db()


# Состояния для формы отзыва
class ReviewState(StatesGroup):
    rating = State()
    comment = State()


# Главное меню
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📸 Услуги и цены"),
            KeyboardButton(text="🏛 Наши залы"),
        ],
        [
            KeyboardButton(text="📅 Записаться на съёмку"),
            KeyboardButton(text="⭐ Отзывы и оценки"),
        ],
        [
            KeyboardButton(text="✍️ Оставить отзыв"),
            KeyboardButton(text="❓ Помощь"),
        ],
    ],
    resize_keyboard=True,
)


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_text = (
        f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
        "Добро пожаловать в бота поддержки фотомастерской "
        "**«ТЁПЛЫЙ КАДР»**! 📷✨\n\n"
        "Чем мы можем вам помочь? Выберите нужный раздел в меню ниже:"
    )
    await message.answer(
        welcome_text,
        reply_markup=main_keyboard,
        parse_mode="Markdown",
    )


@dp.message(F.text == "📸 Услуги и цены")
async def show_services(message: types.Message):
    text = (
        "<b>💳 Наши пакеты и услуги:</b>\n\n"
        "1. <b>Пакет «Индивидуальный»</b> — 5 000 ₽ / час\n"
        "2. <b>Пакет «Плёночная история»</b> — 7 500 ₽\n"
        "3. <b>Аренда съёмочного зала</b> — от 1 800 ₽ / час."
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(F.text == "🏛 Наши залы")
async def show_halls(message: types.Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Зал «Винтаж» 🛋", callback_data="hall_vintage")],
            [InlineKeyboardButton(text="Зал «Светлый лофт» ☀️", callback_data="hall_loft")],
        ]
    )
    await message.answer(
        "Выберите съёмочную локацию для просмотра подробностей:",
        reply_markup=kb,
    )


@dp.callback_query(F.data.startswith("hall_"))
async def hall_info(callback: types.CallbackQuery):
    if callback.data == "hall_vintage":
        await callback.message.answer(
            "🛋 <b>Зал «Винтаж»</b>\n"
            "Уютная локация с винтажной мебелью и тёплым светом. "
            "2 000 ₽/час.",
            parse_mode="HTML",
        )
    elif callback.data == "hall_loft":
        await callback.message.answer(
            "☀️ <b>Зал «Светлый лофт»</b>\n"
            "Просторный интерьер с большими окнами. 1 800 ₽/час.",
            parse_mode="HTML",
        )
    await callback.answer()


# Просмотр статистики отзывов из БД
@dp.message(F.text == "⭐ Отзывы и оценки")
async def show_reviews(message: types.Message):
    avg_rating, count = database.get_reviews_stat()
    text = (
        f"<b>⭐ Отзывы клиентов фотомастерской «ТЁПЛЫЙ КАДР»:</b>\n\n"
        f"📊 Средняя оценка студии в БД: <b>{avg_rating} / 5.0</b> ★\n"
        f"💬 Всего оставлено отзывов: <b>{count}</b>\n\n"
        "Чтобы оставить свой отзыв, нажмите кнопку "
        "<b>«✍️ Оставить отзыв»</b>!"
    )
    await message.answer(text, parse_mode="HTML")


# НАЧАЛО СЦЕНАРИЯ ОСТАВЛЕНИЯ ОТЗЫВА
@dp.message(F.text == "✍️ Оставить отзыв")
async def start_review(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 ⭐", callback_data="rate_1"),
                InlineKeyboardButton(text="2 ⭐", callback_data="rate_2"),
                InlineKeyboardButton(text="3 ⭐", callback_data="rate_3"),
                InlineKeyboardButton(text="4 ⭐", callback_data="rate_4"),
                InlineKeyboardButton(text="5 ⭐", callback_data="rate_5"),
            ]
        ]
    )
    await message.answer(
        "Пожалуйста, оцените работу фотомастерской от 1 до 5 звёзд:",
        reply_markup=kb,
    )
    await state.set_state(ReviewState.rating)


@dp.callback_query(F.data.startswith("rate_"), ReviewState.rating)
async def process_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await callback.message.answer(
        f"Вы поставили {rating} ★. "
        "Теперь напишите ваш текстовый отзыв или комментарий:"
    )
    await state.set_state(ReviewState.comment)
    await callback.answer()


@dp.message(ReviewState.comment)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    rating = data["rating"]
    comment = message.text
    user_name = message.from_user.first_name

    # Сохраняем в БД
    database.add_review(user_name, rating, comment)

    await message.answer(
        "❤️ Спасибо за ваш отзыв! Он успешно сохранён в нашей базе данных."
    )
    await state.clear()


@dp.message(F.text == "📅 Записаться на съёмку")
async def book_slot(message: types.Message):
    await message.answer(
        "Для оформления заявки свяжитесь с администратором: "
        "@TeplyKadr_Admin или позвоните +7 (812) 000-00-00."
    )


@dp.message(F.text == "❓ Помощь")
async def help_cmd(message: types.Message):
    await message.answer(
        "По всем вопросам пишите старшему администратору: @TeplyKadr_Admin"
    )


async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Обновлённый бот фотостудии с БД успешно запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())