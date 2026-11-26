import asyncio
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    FSInputFile,
    ReplyKeyboardRemove
)


import database

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
database.init_db()

# --- FSM СОСТОЯНИЯ ---
class BookingState(StatesGroup):
    hall = State()
    date = State()
    time = State()
    phone = State()

class ReviewState(StatesGroup):
    rating = State()
    comment = State()

class PrintOrderState(StatesGroup):
    waiting_for_photos = State()
    format_choice = State()
    phone = State()

# --- ГЛАВНОЕ МЕНЮ ---
def get_main_menu():
    buttons = [
        [InlineKeyboardButton(text="📸 Услуги и цены", callback_data="show_services"),
         InlineKeyboardButton(text="🏛 Наши залы", callback_data="show_halls")],
        [InlineKeyboardButton(text="📅 Забронировать зал", callback_data="start_booking"),
         InlineKeyboardButton(text="🖨 Печать фото", callback_data="start_print")],
        [InlineKeyboardButton(text="⭐ Отзывы студии", callback_data="show_reviews"),
         InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="write_review")],
        [InlineKeyboardButton(text="📍 Адрес и контакты", callback_data="show_contacts"),
         InlineKeyboardButton(text="❓ FAQ / Вопросы", callback_data="show_faq")],
        [InlineKeyboardButton(text="📱 Мы в соцсетях ✨", url="https://t.me/telegram")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# --- /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Удаляем старую нижнюю клавиатуру, если у кого-то осталась, но не мусорим в чате
    msg = await message.answer("⏳", reply_markup=ReplyKeyboardRemove())
    await msg.delete()

    # Отправляем то самое красивое приветствие с фото фотоаппарата
    await message.answer_photo(
        photo="https://images.unsplash.com/photo-1542038784456-1ea8e935640e?q=80&w=1000",
        caption=(
            f"<b>Здравствуйте, {message.from_user.first_name}! 👋</b>\n\n"
            "Добро пожаловать в «ТЁПЛЫЙ КАДР».\n"
            "Выберите действие в меню ниже:"
        ),
        reply_markup=get_main_menu(),
        parse_mode="HTML"
    )
   

# --- УСЛУГИ И ЦЕНЫ ---
@dp.callback_query(F.data == "show_services")
@dp.message(Command("services"))
async def services(event: types.CallbackQuery | types.Message):
    text = (
        "<b>💳 Услуги фотомастерской «ТЁПЛЫЙ КАДР»:</b>\n\n"
        "🎬 <b>Пакет «Индивидуальный»</b> — 5 000 ₽ / час\n"
        "   • 1 час съёмки, 15 кадров в ретуши, все исходники.\n\n"
        "🎞 <b>Пакет «Плёночная история»</b> — 7 500 ₽\n"
        "   • Винтажная съёмка на плёнку 35mm + оцифровка.\n\n"
        "🖨 <b>Экспресс-печать снимков</b> — от 35 ₽ / шт.\n"
        "   • Загрузите фото прямо в бота и заберите в студии!\n\n"
        "🏛 <b>Аренда залов</b> — от 1 800 ₽ / час."
    )
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

# --- АДРЕС И КОНТАКТЫ ---
@dp.callback_query(F.data == "show_contacts")
@dp.message(Command("contacts"))
async def contacts(event: types.CallbackQuery | types.Message):
    text = (
        "<b>📍 Как нас найти:</b>\n\n"
        "🏢 <b>Адрес:</b> г. Санкт-Петербург, ул. Большая Морская, д. 67 (5 минут от ст. м. «Адмиралтейская» / «Садовая»)\n"
        "⏰ <b>Часы работы:</b> ежедневно с 10:00 до 22:00\n"
        "📞 <b>Телефон:</b> +7 (812) 400-20-26\n"
        "💬 <b>Администратор в Telegram:</b> @TeplyKadr_Admin\n\n"
        "☕ В студии всегда есть чай, кофе и уютная зона ожидания!"
    )
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

# --- НАШИ ЗАЛЫ (с локальными фото) ---
@dp.callback_query(F.data == "show_halls")
@dp.message(Command("halls"))
async def halls(event: types.CallbackQuery | types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зал «Винтаж» 🛋", callback_data="h_vintage"),
         InlineKeyboardButton(text="Зал «Лофт» ☀️", callback_data="h_loft")]
    ])
    text = "Выберите зал, чтобы посмотреть реальные фотографии интерьера и оборудования:"
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=kb)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("h_"))
async def hall_info(callback: types.CallbackQuery):
    if callback.data == "h_vintage":
        caption = (
            "🛋 <b>Зал «Винтаж»</b>\n\n"
            "• Уютная библиотека, винтажная мебель, мягкий тёплый свет.\n"
            "• Идеально для ретро-сессий, портретов и съёмок с книгами.\n"
            "• <b>Стоимость:</b> 2 000 ₽ / час"
        )
        if os.path.exists("vintage.jpg"):
            photo = FSInputFile("vintage.jpg")
            await callback.message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
        else:
            await callback.message.answer(caption, parse_mode="HTML")
    else:
        caption = (
            "☀️ <b>Зал «Светлый лофт»</b>\n\n"
            "• Белая кирпичная кладка, высокие потолки, панорамные окна.\n"
            "• Естественный рассеянный свет и профессиональные импульсные приборы.\n"
            "• <b>Стоимость:</b> 1 800 ₽ / час"
        )
        if os.path.exists("loft.jpg"):
            photo = FSInputFile("loft.jpg")
            await callback.message.answer_photo(photo=photo, caption=caption, parse_mode="HTML")
        else:
            await callback.message.answer(caption, parse_mode="HTML")
    await callback.answer()

# --- БРОНИРОВАНИЕ С КНОПКАМИ ДАТЫ И ВРЕМЕНИ ---
@dp.callback_query(F.data == "start_booking")
@dp.message(Command("book"))
async def start_booking(event: types.CallbackQuery | types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Винтаж 🛋", callback_data="b_vintage"),
         InlineKeyboardButton(text="Светлый лофт ☀️", callback_data="b_loft")]
    ])
    text = "<b>Шаг 1 из 4:</b> Выберите зал для бронирования:"
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingState.hall)

@dp.callback_query(BookingState.hall)
async def book_hall_selected(callback: types.CallbackQuery, state: FSMContext):
    hall_name = "Винтаж" if callback.data == "b_vintage" else "Светлый лофт"
    await state.update_data(hall=hall_name)

    # Генерируем кнопки на 3 ближайших дня
    today = datetime.now()
    d1 = today.strftime("%d.%m")
    d2 = (today + timedelta(days=1)).strftime("%d.%m")
    d3 = (today + timedelta(days=2)).strftime("%d.%m")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Сегодня ({d1})", callback_data=f"date_{d1}"),
         InlineKeyboardButton(text=f"Завтра ({d2})", callback_data=f"date_{d2}")],
        [InlineKeyboardButton(text=f"Послезавтра ({d3})", callback_data=f"date_{d3}")]
    ])
    await callback.message.answer(f"Выбран зал: <b>{hall_name}</b>.\n<b>Шаг 2 из 4:</b> Выберите дату:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingState.date)
    await callback.answer()
@dp.callback_query(BookingState.date)
async def book_date_selected(callback: types.CallbackQuery, state: FSMContext):
    selected_date = callback.data.replace("date_", "")
    await state.update_data(date=selected_date)

    # Слоты по расписанию студии
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="11:00 - 12:00", callback_data="time_11:00"),
         InlineKeyboardButton(text="13:00 - 14:00", callback_data="time_13:00")],
        [InlineKeyboardButton(text="15:00 - 16:00", callback_data="time_15:00"),
         InlineKeyboardButton(text="17:00 - 18:00", callback_data="time_17:00")],
        [InlineKeyboardButton(text="19:00 - 20:00", callback_data="time_19:00")]
    ])
    await callback.message.answer(f"Дата: <b>{selected_date}</b>.\n<b>Шаг 3 из 4:</b> Выберите свободное время:", reply_markup=kb, parse_mode="HTML")
    await state.set_state(BookingState.time)
    await callback.answer()

@dp.callback_query(BookingState.time)
async def book_time_selected(
    callback: types.CallbackQuery,
    state: FSMContext
):
    selected_time = callback.data.replace("time_", "")
    await state.update_data(time=selected_time)

    await callback.message.answer(
        "<b>Шаг 4 из 4:</b>\n"
        "Отправьте номер телефона для подтверждения бронирования.",
        parse_mode="HTML"
    )

    await state.set_state(BookingState.phone)
    await callback.answer()

@dp.message(BookingState.phone)
async def book_phone_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    phone = message.text
    full_datetime = f"{data['date']} в {data['time']}"

    # Сохранение в БД
    database.add_booking(user, data['hall'], full_datetime, phone)

    # Уведомление администратору
    admin_text = (
        "🚨 <b>НОВАЯ БРОНЬ В СТУДИИ!</b>\n\n"
        f"👤 <b>Клиент:</b> {user} ({username})\n"
        f"🏛 <b>Зал:</b> {data['hall']}\n"
        f"📅 <b>Дата и слот:</b> {full_datetime}\n"
        f"📞 <b>Телефон:</b> {phone}\n\n"
        "<i>Заявка автоматически зафиксирована в базе данных.</i>"
    )
    if ADMIN_ID != 0:
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление админу: {e}")

    # Ответ клиенту
    await message.answer(
        f"✅ <b>Заявка успешно оформлена!</b>\n\n"
        f"🏛 Зал: {data['hall']}\n"
        f"📅 Время: {full_datetime}\n"
        f"📍 Адрес: ул. Большая Морская, 67\n\n"
        f"🔔 <i>Мы пришлём вам напоминание в этот чат за 24 часа до съёмки! До встречи в «Тёплом Кадре»!</i>",
        parse_mode="HTML"
    )
    await state.clear()

# --- СЕРВИС: ОНЛАЙН-ПЕЧАТЬ ФОТОГРАФИЙ ---
@dp.callback_query(F.data == "start_print")
@dp.message(Command("print"))
async def start_print(event: types.CallbackQuery | types.Message, state: FSMContext):
       kb = InlineKeyboardMarkup(inline_keyboard=[
           [InlineKeyboardButton(text="10 × 15 (Стандарт)", callback_data="pformat_10x15"),
            InlineKeyboardButton(text="Полароид (Ретро)", callback_data="pformat_polaroid")],
           [InlineKeyboardButton(text="А4 (Большой)", callback_data="pformat_A4")]
       ])
       text = "🖨 <b>Печать фото:</b>\nВыберите желаемый формат:"
       if isinstance(event, types.CallbackQuery):
           await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
           await event.answer()
       else:
           await event.answer(text, reply_markup=kb, parse_mode="HTML")
       await state.set_state(PrintOrderState.format_choice)
   
@dp.callback_query(PrintOrderState.format_choice)
async def print_format_chosen(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.replace("pformat_", "")
    await state.update_data(chosen_format=fmt)
    await callback.message.answer(
        f"Формат: <b>{fmt}</b>.\n\n"
        "📎 Теперь <b>отправьте сюда фотографии</b> (как фото или файл без сжатия), которые нужно напечатать!",
        parse_mode="HTML"
    )
    await state.set_state(PrintOrderState.waiting_for_photos)
    await callback.answer()
@dp.message(PrintOrderState.waiting_for_photos, F.photo | F.document)
async def print_photo_received(message: types.Message, state: FSMContext):
    # Запоминаем file_id фото/документа
    if message.photo:
        await state.update_data(file_type="photo", file_id=message.photo[-1].file_id)
    else:
        await state.update_data(file_type="doc", file_id=message.document.file_id)
    
    await message.answer("📎 Фото получено! Теперь введите ваш номер телефона для уведомления о готовности:")
    await state.set_state(PrintOrderState.phone)

@dp.message(PrintOrderState.phone)
async def print_phone_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    fmt = data.get("chosen_format", "10x15")
    user = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    phone = message.text

    if ADMIN_ID != 0:
        caption = (
            f"🖨 <b>ЗАКАЗ НА ПЕЧАТЬ!</b>\n"
            f"👤 Клиент: {user} ({username})\n"
            f"📞 Телефон: {phone}\n"
            f"📐 Формат: {fmt}"
        )
        if data["file_type"] == "photo":
            await bot.send_photo(ADMIN_ID, photo=data["file_id"], caption=caption, parse_mode="HTML")
        else:
            await bot.send_document(ADMIN_ID, document=data["file_id"], caption=caption, parse_mode="HTML")

    await message.answer("✅ Заказ на печать оформлен! Мы свяжемся с вами, когда снимки будут готовы на Большой Морской, 67.")
    await state.clear()

# --- ОТЗЫВЫ: СОХРАНЕНИЕ + ОПОВЕЩЕНИЕ АДМИНА ---
@dp.callback_query(F.data == "show_reviews")
@dp.message(Command("reviews"))
async def show_reviews(event: types.CallbackQuery | types.Message):
    avg, count = database.get_reviews_stat()
    text = (
        f"⭐ <b>Рейтинг студии «ТЁПЛЫЙ КАДР»: {avg} / 5.0</b>\n"
        f"💬 Всего проверенных отзывов: <b>{count}</b>\n\n"
        "Нажмите <i>«✍️ Оставить отзыв»</i>, чтобы поделиться своими впечатлениями!"
    )
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")

@dp.callback_query(F.data == "write_review")
@dp.message(Command("feedback"))
async def start_review(event: types.CallbackQuery | types.Message, state: FSMContext):
       kb = InlineKeyboardMarkup(inline_keyboard=[
           [InlineKeyboardButton(text="1 ⭐", callback_data="rate_1"),
            InlineKeyboardButton(text="2 ⭐", callback_data="rate_2"),
            InlineKeyboardButton(text="3 ⭐", callback_data="rate_3"),
            InlineKeyboardButton(text="4 ⭐", callback_data="rate_4"),
            InlineKeyboardButton(text="5 ⭐", callback_data="rate_5")]
       ])
       text = "Оцените качество работы студии и фотографов:"
       if isinstance(event, types.CallbackQuery):
           await event.message.answer(text, reply_markup=kb)
           await event.answer()
       else:
           await event.answer(text, reply_markup=kb)
       await state.set_state(ReviewState.rating)
   

@dp.callback_query(F.data.startswith("rate_"), ReviewState.rating)
async def review_rate(callback: types.CallbackQuery, state: FSMContext):
    rating = callback.data.replace("rate_", "")
    await state.update_data(rating=rating)
    await callback.message.answer(f"Ваша оценка: {rating} ★. Теперь напишите пару слов о ваших впечатлениях:")
    await state.set_state(ReviewState.comment)
    await callback.answer()

@dp.message(ReviewState.comment)
async def review_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    rating = data['rating']
    text = message.text
    user = message.from_user.full_name
    username = f"@{message.from_user.username}" if message.from_user.username else ""

    # Сохраняем в базу данных
    database.add_review(user, int(rating), text)

    # МГНОВЕННОЕ УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ О НОВОМ ОТЗЫВЕ!
    if ADMIN_ID != 0:
        admin_alert = (
            "🌟 <b>ПОСТУПИЛ НОВЫЙ ОТЗЫВ!</b>\n\n"
            f"👤 Автор: {user} {username}\n"
            f"⭐ Оценка: {rating} / 5\n"
            f"💬 Текст отзыва:\n<i>«{text}»</i>"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_alert, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Не удалось отправить отзыв админу: {e}")

    await message.answer("❤️ Большое спасибо за ваш отзыв! Он помогает нам становиться лучше.")
    await state.clear()

# --- FAQ ---
@dp.callback_query(F.data == "show_faq")
@dp.message(Command("help"))
async def faq(event: types.CallbackQuery | types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сроки готовности фото ⏱", callback_data="f_time")],
        [InlineKeyboardButton(text="Можно ли с животными? 🐾", callback_data="f_pets")],
        [InlineKeyboardButton(text="Как задать свой вопрос? ❓", callback_data="f_ask")]
    ])
    text = "<b>Часто задаваемые вопросы (FAQ):</b>"
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("f_"))
async def faq_answers(callback: types.CallbackQuery):
    if callback.data == "f_time":
        ans = "⏱ <b>Сроки:</b> Первые исходники доступны в течение 48 часов. Полная ретушь серии — до 10 рабочих дней."
    elif callback.data == "f_pets":
        ans = "🐾 <b>Pet-friendly:</b> Да! Мы рады пушистым гостям любого размера. Доплата за клининг после съёмки — 500 ₽."
    else:
        ans = "💬 Вы можете задать любой вопрос нашему старшему администратору напрямую: @TeplyKadr_Admin"
    await callback.message.answer(ans, parse_mode="HTML")
    await callback.answer()
@dp.message(Command("admin_reviews"))
async def admin_reviews(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ Эта команда доступна только администратору.")
        return

    reviews = database.get_recent_reviews()

    if not reviews:
        await message.answer("Пока отзывов нет.")
        return

    lines = ["⭐ Последние отзывы:\n"]
    for name, rating, comment in reviews:
        lines.append(
            f"👤 {name}\n"
            f"Оценка: {rating}/5\n"
            f"Отзыв: {comment}\n"
        )

    await message.answer("\n".join(lines))
# --- ТОЧКА ЗАПУСКА ---
async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 Полнофункциональный бот фотостудии «ТЁПЛЫЙ КАДР» запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())