import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import database

# Загрузка токена из скрытого файла .env
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
database.init_db()

# Состояния для бронирования и отзывов
class BookingState(StatesGroup):
    hall = State()
    date_time = State()
    phone = State()

class ReviewState(StatesGroup):
    rating = State()
    comment = State()

# Функция главного меню (Inline-кнопки под сообщением)
def main_menu():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Услуги и цены", callback_data="show_services")],
        [InlineKeyboardButton(text="🏛 Наши залы", callback_data="show_halls")],
        [InlineKeyboardButton(text="📅 Забронировать слот", callback_data="start_booking")],
        [InlineKeyboardButton(text="⭐ Отзывы и оценки", callback_data="show_reviews")],
        [InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="write_review")],
        [InlineKeyboardButton(text="❓ FAQ (Вопросы)", callback_data="show_faq")],
        [InlineKeyboardButton(text="📱 Мы в соцсетях ✨", url="https://t.me/telegram")]
    ])
    return kb

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer_photo(
        photo="https://images.unsplash.com/photo-1542038784456-1ea8e935640e?q=80&w=1000",
        caption=f"<b>Здравствуйте, {message.from_user.first_name}! 👋</b>\n\nДобро пожаловать в фотомастерскую <b>«ТЁПЛЫЙ КАДР»</b>.\nВыберите интересующий раздел в меню ниже:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

# --- УСЛУГИ ---
@dp.callback_query(F.data == "show_services")
async def services(callback: types.CallbackQuery):
    text = (
        "<b>💳 Наши услуги:</b>\n\n"
        "🎬 Пакет «Индивидуальный» — 5 000 ₽\n"
        "🎞 Пакет «Плёночный» — 7 500 ₽\n"
        "📸 Семейная съёмка — 6 500 ₽"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# --- ЗАЛЫ ---
@dp.callback_query(F.data == "show_halls")
async def halls(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зал «Винтаж» 🛋", callback_data="h_vintage")],
        [InlineKeyboardButton(text="Зал «Светлый лофт» ☀️", callback_data="h_loft")]
    ])
    await callback.message.answer("Наши съемочные локации:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("h_"))
async def hall_info(callback: types.CallbackQuery):
    photo = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?q=80&w=1000"
    await callback.message.answer_photo(photo=photo, caption="Уютная локация с профессиональным оборудованием. Цена: 2000р/час.")
    await callback.answer()

# --- FAQ ---
@dp.callback_query(F.data == "show_faq")
async def faq(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сроки готовности фото", callback_data="f_time")],
        [InlineKeyboardButton(text="Можно ли с животными?", callback_data="f_pets")]
    ])
    await callback.message.answer("Часто задаваемые вопросы:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("f_"))
async def faq_ans(callback: types.CallbackQuery):
    answer = "📸 Отбор фото занимает 3 дня, ретушь — до 14 дней." if callback.data == "f_time" else "🐾 Да, мы pet-friendly!"
    await callback.message.answer(answer)
    await callback.answer()
# --- БРОНИРОВАНИЕ (Цепочка действий) ---
@dp.callback_query(F.data == "start_booking")
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Винтаж", callback_data="b_vintage"), 
         InlineKeyboardButton(text="Лофт", callback_data="b_loft")]
    ])
    await callback.message.answer("Какой зал вы хотите забронировать?", reply_markup=kb)
    await state.set_state(BookingState.hall)
    await callback.answer()

@dp.callback_query(BookingState.hall)
async def book_hall(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(hall=callback.data)
    await callback.message.answer("Напишите желаемую дату и время (например: 25 ноября, 18:00):")
    await state.set_state(BookingState.date_time)
    await callback.answer()

@dp.message(BookingState.date_time)
async def book_time(message: types.Message, state: FSMContext):
    await state.update_data(date_time=message.text)
    await message.answer("Ваш номер телефона для связи:")
    await state.set_state(BookingState.phone)

@dp.message(BookingState.phone)
async def book_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    database.add_booking(message.from_user.full_name, data['hall'], data['date_time'], message.text)
    await message.answer(f"✅ Заявка принята! Мы свяжемся с вами по номеру {message.text}.")
    await state.clear()

# --- ОТЗЫВЫ ---
@dp.callback_query(F.data == "show_reviews")
async def reviews(callback: types.CallbackQuery):
    avg, count = database.get_reviews_stat()
    await callback.message.answer(f"⭐ Рейтинг студии: {avg}/5.0\n💬 Оставлено отзывов: {count}")
    await callback.answer()

@dp.callback_query(F.data == "write_review")
async def write_rev(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Оцените нашу работу от 1 до 5:")
    await state.set_state(ReviewState.rating)
    await callback.answer()

@dp.message(ReviewState.rating)
async def rev_rate(message: types.Message, state: FSMContext):
    await state.update_data(rating=message.text)
    await message.answer("Напишите ваш текст отзыва:")
    await state.set_state(ReviewState.comment)

@dp.message(ReviewState.comment)
async def rev_comm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    database.add_review(message.from_user.first_name, data['rating'], message.text)
    await message.answer("❤️ Спасибо за обратную связь!")
    await state.clear()

async def main():
    print("🚀 Бот фотостудии успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
