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

# Загрузка настроек
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# ВСТАВЬ СЮДА СВОЙ ID (который получил от @userinfobot), ЧТОБЫ ПОЛУЧАТЬ УВЕДОМЛЕНИЯ:
ADMIN_ID = int(os.getenv("ADMIN_ID"))



bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
database.init_db()

# Состояния
class BookingState(StatesGroup):
    hall = State()
    date_time = State()
    phone = State()

class ReviewState(StatesGroup):
    rating = State()
    comment = State()

# --- ГЛАВНОЕ МЕНЮ (Плитка как на фото) ---
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="📸 Услуги и цены", callback_data="show_services"),
         InlineKeyboardButton(text="🏛 Наши залы", callback_data="show_halls")],
        [InlineKeyboardButton(text="📅 Забронировать слот", callback_data="start_booking")],
        [InlineKeyboardButton(text="⭐ Отзывы", callback_data="show_reviews"),
         InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="write_review")],
        [InlineKeyboardButton(text="❓ Помощь / FAQ", callback_data="show_faq")],
        [InlineKeyboardButton(text="📱 Мы в соцсетях ✨", url="https://t.me/telegram")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer_photo(
        photo="https://images.unsplash.com/photo-1542038784456-1ea8e935640e?q=80&w=1000",
        caption=f"<b>Здравствуйте, {message.from_user.first_name}! 👋</b>\n\nДобро пожаловать в «ТЁПЛЫЙ КАДР».\nВыберите действие в меню ниже:",
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )

# --- УСЛУГИ ---
@dp.callback_query(F.data == "show_services")
async def services(callback: types.CallbackQuery):
    text = "<b>💳 Наши услуги:</b>\n\n🎬 Пакет «Индивидуальный» — 5 000 ₽\n🎞 Пакет «Плёночный» — 7 500 ₽\n📸 Семейная съёмка — 6 500 ₽"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# --- ЗАЛЫ (Разные картинки) ---
@dp.callback_query(F.data == "show_halls")
async def halls(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зал «Винтаж» 🛋", callback_data="h_vintage")],
        [InlineKeyboardButton(text="Зал «Лофт» ☀️", callback_data="h_loft")]
    ])
    await callback.message.answer("Выберите зал для просмотра фото:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("h_"))
async def hall_info(callback: types.CallbackQuery):
    if callback.data == "h_vintage":
        img = "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?q=80&w=1000"
        cap = "🛋 <b>Зал «Винтаж»</b>\nРетро-мебель, теплый свет. 2000р/час."
    else:
        img = "https://images.unsplash.com/photo-1493809842364-78817add7ffb?q=80&w=1000"
        cap = "☀️ <b>Зал «Светлый лофт»</b>\nМинимализм, огромные окна. 1800р/час."
    
    await callback.message.answer_photo(photo=img, caption=cap, parse_mode="HTML")
    await callback.answer()

# --- БРОНИРОВАНИЕ (С уведомлением админа) ---
@dp.callback_query(F.data == "start_booking")
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Винтаж 🛋", callback_data="b_v"), 
         InlineKeyboardButton(text="Лофт ☀️", callback_data="b_l")]
    ])
    await callback.message.answer("Какой зал бронируем?", reply_markup=kb)
    await state.set_state(BookingState.hall)
    await callback.answer()
@dp.callback_query(BookingState.hall)
async def book_hall(callback: types.CallbackQuery, state: FSMContext):
    hall_name = "Винтаж" if callback.data == "b_v" else "Лофт"
    await state.update_data(hall=hall_name)
    await callback.message.answer(f"Выбран зал: {hall_name}. Напишите дату и время:")
    await state.set_state(BookingState.date_time)
    await callback.answer()

@dp.message(BookingState.date_time)
async def book_time(message: types.Message, state: FSMContext):
    await state.update_data(date_time=message.text)
    await message.answer("Введите ваш номер телефона:")
    await state.set_state(BookingState.phone)

@dp.message(BookingState.phone)
async def book_phone(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user.full_name
    phone_num = message.text

    # 1. Сохраняем в базу данных
    database.add_booking(user, data.get('hall', 'Не указан'), data.get('date_time', 'Не указано'), phone_num)
    
    # 2. Текст для администратора (простой и надежный)
    admin_msg = (
        "🔔 НОВАЯ ЗАЯВКА НА БРОНИРОВАНИЕ!\n\n"
        f"👤 Клиент: {user}\n"
        f"🏛 Зал: {data.get('hall')}\n"
        f"📅 Время: {data.get('date_time')}\n"
        f"📞 Телефон: {phone_num}"
    )
    
    # 3. Отправка администратору с выводом реальной ошибки в консоль
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        print("✅ Уведомление успешно отправлено администратору в Telegram!")
    except Exception as e:
        print(f"❌ Ошибка отправки админу: {e}")

    await message.answer("✅ Ваша заявка принята! Администратор свяжется с вами в ближайшее время.")
    await state.clear()

# --- ОТЗЫВЫ, FAQ и запуск (оставил как в прошлый раз) ---
@dp.callback_query(F.data == "show_reviews")
async def reviews(callback: types.CallbackQuery):
    avg, count = database.get_reviews_stat()
    await callback.message.answer(f"⭐ Рейтинг: {avg}/5.0\n💬 Отзывов: {count}")
    await callback.answer()

async def main():
    print("🚀 Senior-бот запущен! Проверьте Telegram.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())