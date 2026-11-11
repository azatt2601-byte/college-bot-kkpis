import os
import asyncio
import logging
import sqlite3
from datetime import date, datetime
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, CallbackQuery, 
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = os.getenv("BOT_TOKEN", "9014605842:AAElbRDb2o2cpOziIacy5w5KNvLxcU3rcPU")

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

BAD_WORDS = ["мат1", "мат2", "блять", "сука", "хуй", "пизда", "ебать", "сучка"]

def check_bad_words(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for word in BAD_WORDS:
        if word in text_lower:
            return True
    return False

def init_db():
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT,
            fio TEXT,
            group_name TEXT,
            phone TEXT,
            lang TEXT DEFAULT 'ru',
            registered INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category TEXT,
            portion_grams INTEGER,
            kbzh TEXT,
            allergens TEXT,
            ingredients TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_date TEXT,
            category TEXT,
            dish_text TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT,
            photo_id TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title_text TEXT,
            photo_id TEXT,
            event_date TEXT,
            location TEXT,
            need_students INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER,
            user_id INTEGER,
            fio TEXT,
            group_name TEXT,
            skill TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fio TEXT,
            group_name TEXT,
            text TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS polls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            options TEXT,
            active INTEGER DEFAULT 1
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS poll_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            poll_id INTEGER,
            user_id INTEGER,
            fio TEXT,
            group_name TEXT,
            answer TEXT,
            timestamp TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appeals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fio TEXT,
            group_name TEXT,
            text TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'unread'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_pass', 'admin12345')")
    conn.commit()
    conn.close()

class RegistrationFlow(StatesGroup):
    role = State()
    fio = State()
    group = State()
    phone = State()

class SearchDishState(StatesGroup):
    query = State()

class ReviewState(StatesGroup):
    rating = State()
    text = State()

class EventApplyState(StatesGroup):
    skill = State()

class IdeaState(StatesGroup):
    text = State()

class AppealState(StatesGroup):
    text = State()

class AdminAuthState(StatesGroup):
    password = State()

class AdminChangePass(StatesGroup):
    old_pass = State()
    new_pass1 = State()
    new_pass2 = State()

class AdminAddMenu(StatesGroup):
    text = State()

class AdminAddDish(StatesGroup):
    name = State()
    category = State()
    grams = State()
    kbzh = State()
    allergens = State()
    ingredients = State()

class AdminSchedule(StatesGroup):
    content = State()

class AdminEvent(StatesGroup):
    photo = State()
    title = State()
    need_people = State()
    date = State()
    location = State()

class AdminBroadcast(StatesGroup):
    text = State()

def get_main_keyboard(lang="ru"):
    if lang == "kz":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🍽 Меню"), KeyboardButton(text="📅 Кесте")],
                [KeyboardButton(text="🎉 Іс-шаралар"), KeyboardButton(text="💡 Колледж идеялары")],
                [KeyboardButton(text="📊 Сауалнамалар"), KeyboardButton(text="📞 Тікелей байланыс")],
                [KeyboardButton(text="🌐 Тілді өзгерту"), KeyboardButton(text="ℹ️ Көмек")],
                [KeyboardButton(text="🔄 Қайта іске қосу"), KeyboardButton(text="🔐 Әкімшілік")]
            ],
            resize_keyboard=True
        )
    else:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🍽 Меню"), KeyboardButton(text="📅 Расписание")],
                [KeyboardButton(text="🎉 Мероприятия"), KeyboardButton(text="💡 Идеи для колледжа")],
                [KeyboardButton(text="📊 Опросы"), KeyboardButton(text="📞 Прямая связь")],
                [KeyboardButton(text="🌐 Смена языка"), KeyboardButton(text="ℹ️ Помощь")],
                [KeyboardButton(text="🔄 Перезапуск"), KeyboardButton(text="🔐 Админка")]
            ],
            resize_keyboard=True
        )

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered, lang FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user and user[0] == 1:
        lang = user[1]
        await message.answer("👋 Главное меню:", reply_markup=get_main_keyboard(lang))
        return
        
    welcome_text = (
        "🇰🇿 Колледж басқару ботына қош келдіңіз!\n"
        "🇷🇺 Добро пожаловать в бот управления колледжем!\n\n"
        "🌐 Тілді таңдаңыз / Выберите язык:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
         InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="lang_kz")]
    ])
    await message.answer(welcome_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("lang_"))
async def process_lang(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="do_reg"),
         InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip_reg")]
    ]) if lang == "ru" else InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Тіркелу", callback_data="do_reg"),
         InlineKeyboardButton(text="⏭ Өтіп кету", callback_data="skip_reg")]
    ])
    
    text = "Желаете пройти обязательную регистрацию? (Без нее часть функций будет недоступна)" if lang == "ru" else "Міндетті тіркеуден өткіңіз келе ме?"
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "skip_reg")
async def skip_registration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, lang, registered) VALUES (?, ?, 0)", (user_id, lang))
    conn.commit()
    conn.close()
    
    await callback.message.answer("⚠️ Вы вошли в гостевом режиме. Некоторые функции заблокированы.", reply_markup=get_main_keyboard(lang))
    await state.clear()

@router.callback_query(F.data == "do_reg")
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("lang", "ru")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👨‍🎓 Студент", callback_data="role_student"),
         InlineKeyboardButton(text="👩‍🏫 Учитель", callback_data="role_teacher")]
    ])
    text = "Выберите вашу роль:" if lang == "ru" else "Рөліңізді таңдаңыз:"
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("role_"))
async def process_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    role = callback.data.split("_")[1]
    await state.update_data(role=role)
    await state.set_state(RegistrationFlow.fio)
    await callback.message.answer("Введите ваши ФИО (Фамилия Имя Отчество):")

@router.message(RegistrationFlow.fio)
async def reg_fio(message: Message, state: FSMContext):
    if check_bad_words(message.text):
        await message.answer("⚠️ Обнаружена нецензурная лексика. Введите корректные ФИО:")
        return
    await state.update_data(fio=message.text)
    data = await state.get_data()
    
    if data["role"] == "student":
        await state.set_state(RegistrationFlow.group)
        await message.answer("Введите вашу учебную группу (например, ИС-21):")
    else:
        await state.set_state(RegistrationFlow.phone)
        await message.answer("Введите ваш номер телефона:")

@router.message(RegistrationFlow.group)
async def reg_group(message: Message, state: FSMContext):
    await state.update_data(group=message.text)
    await state.set_state(RegistrationFlow.phone)
    await message.answer("Введите ваш номер телефона:")

@router.message(RegistrationFlow.phone)
async def reg_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    lang = data.get("lang", "ru")
    role = data["role"]
    fio = data["fio"]
    group = data.get("group", "-")
    phone = message.text
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, role, fio, group_name, phone, lang, registered) VALUES (?, ?, ?, ?, ?, ?, 1)",
        (user_id, role, fio, group, phone, lang)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Регистрация успешно завершена!", reply_markup=get_main_keyboard(lang))
    await state.clear()

@router.message(F.text.in_(["🔄 Перезапуск", "🔄 Қайта іске қосу"]))
async def restart_bot(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    lang = res[0] if res else "ru"
    await message.answer("🔄 Бот перезапущен.", reply_markup=get_main_keyboard(lang))

@router.message(F.text.in_(["🌐 Смена языка", "🌐 Тілді өзгерту"]))
async def switch_lang_menu(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
         InlineKeyboardButton(text="🇰🇿 Қазақша", callback_data="setlang_kz")]
    ])
    await message.answer("🌐 Выберите язык / Тілді таңдаңыз:", reply_markup=keyboard)

@router.callback_query(F.data.startswith("setlang_"))
async def set_language_final(callback: CallbackQuery):
    await callback.answer()
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()
    
    text = "🌐 Язык изменен!" if lang == "ru" else "🌐 Тіл өзгертілді!"
    await callback.message.answer(text, reply_markup=get_main_keyboard(lang))

@router.message(F.text.in_(["ℹ️ Помощь", "ℹ️ Көмек"]))
async def help_menu(message: Message):
    text = (
        "ℹ️ **Справочная информация и поддержка:**\n\n"
        "💬 По всем вопросам обращайтесь к разработчику: @YourUsername\n\n"
        "🤖 **Часто задаваемые вопросы (FAQ):**\n"
        "• *Как зарегистрироваться?* — Нажмите /start.\n"
        "• *Почему недоступны отзывы?* — Требуется обязательная регистрация.\n"
        "• *Когда обновляется расписание?* — Каждую неделю (скрывается в субботу)."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.text == "🍽 Меню")
async def menu_hub(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍽 Меню на сегодня", callback_data="sub_today_menu")],
        [InlineKeyboardButton(text="🔍 Информация о блюдах", callback_data="sub_dishes_info")],
        [InlineKeyboardButton(text="✍️ Написать отзыв", callback_data="sub_write_review")]
    ])
    await message.answer("🍽 Раздел столовой:", reply_markup=keyboard)

@router.callback_query(F.data == "sub_today_menu")
async def show_today_menu(callback: CallbackQuery):
    await callback.answer()
    today = date.today().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT category, dish_text FROM daily_menu WHERE menu_date = ?", (today,))
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        await callback.message.answer("❌ На сегодня меню еще не добавлено поварами (прошлые меню автоматически скрыты).")
        return
        
    text = f"📋 **Меню на сегодня ({date.today().strftime('%d.%m.%Y')}):**\n\n"
    for cat, d_text in items:
        text += f"▪️ **{cat}**: {d_text}\n"
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "sub_dishes_info")
async def dishes_info_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM dishes")
    dishes = cursor.fetchall()
    conn.close()
    
    text = "🍲 **Доступные блюда в базе:**\n" + ", ".join([d[0] for d in dishes]) if dishes else "База пуста."
    text += "\n\n🔍 Введите название блюда для поиска:"
    await state.set_state(SearchDishState.query)
    await callback.message.answer(text, parse_mode="Markdown")

@router.message(SearchDishState.query)
async def process_dish_search(message: Message, state: FSMContext):
    q = f"%{message.text.strip()}%"
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, portion_grams, kbzh, allergens, ingredients FROM dishes WHERE name LIKE ?", (q,))
    res = cursor.fetchall()
    conn.close()
    
    if not res:
        await message.answer("❌ Ничего не найдено.")
    else:
        for name, g, kb, al, ing in res:
            ans = f"🍲 **{name}**\n⚖️ Порция: {g}г\n🔥 КБЖУ: {kb}\n⚠️ Аллергены: {al}\n🥗 Состав: {ing}"
            await message.answer(ans, parse_mode="Markdown")
    await state.clear()

@router.callback_query(F.data == "sub_write_review")
async def start_review(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    if not res or res[0] == 0:
        await callback.message.answer("⚠️ Для отправки отзыва необходима регистрация (/start).")
        return
        
    await state.set_state(ReviewState.rating)
    await callback.message.answer("⭐ Оцените столовую/блюдо от 1 до 10:")

@router.message(ReviewState.rating)
async def review_rating(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (1 <= int(message.text) <= 10):
        await message.answer("⚠️ Введите число от 1 до 10:")
        return
    await state.update_data(rating=int(message.text))
    await state.set_state(ReviewState.text)
    await message.answer("💬 Напишите текст отзыва:")

@router.message(ReviewState.text)
async def review_text(message: Message, state: FSMContext):
    if check_bad_words(message.text):
        await message.answer("⚠️ ИИ-фильтр заблокировал отзыв: обнаружена нецензурная лексика. Перепишите текст:")
        return
        
    data = await state.get_data()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        await message.answer("Ошибка пользователя.")
        await state.clear()
        return
        
    fio, group = user
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            fio TEXT,
            group_name TEXT,
            rating INTEGER,
            text TEXT,
            timestamp TEXT
        )
    """)
    cursor.execute(
        "INSERT INTO reviews (user_id, fio, group_name, rating, text, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, fio, group, data['rating'], message.text, timestamp)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Спасибо! Ваш отзыв успешно сохранен.")
    await state.clear()

@router.message(F.text.in_(["📅 Расписание", "📅 Кесте"]))
async def show_schedule(message: Message):
    if datetime.now().weekday() == 5:
        await message.answer("📅 В субботу расписание не отображается.")
        return
        
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT link, photo_id FROM schedule ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        await message.answer("📅 Расписание еще не добавлено.")
        return
        
    link, photo_id = row
    if photo_id:
        await message.answer_photo(photo_id, caption="📅 Актуальное расписание:\n🔗 Ссылка: " + str(link))
    else:
        await message.answer("📅 Актуальное расписание:\n🔗 " + str(link))

@router.message(F.text.in_(["🎉 Мероприятия", "🎉 Іс-шаралар"]))
async def show_events(message: Message):
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title_text, photo_id, event_date, location, need_students FROM events")
    events = cursor.fetchall()
    conn.close()
    
    if not events:
        await message.answer("🎉 Нет активных мероприятий.")
        return
        
    for ev_id, title, photo, ev_date, loc, need in events:
        text = f"🎉 **{title}**\n📅 Дата: {ev_date}\n📍 Место: {loc}"
        keyboard = None
        if need == 1:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                InlineKeyboardButton(text="Я хочу участвовать", callback_data=...)
                
