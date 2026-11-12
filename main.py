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
        "💬 По всем вопросам обращайтесь к разработчику\n\n"
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
        await callback.message.answer("❌ На сегодня меню еще не добавлено поварами.")
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
        await message.answer("⚠️ Обнаружена нецензурная лексика. Перепишите текст:")
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
                [InlineKeyboardButton(text="Я хочу участвовать", callback_data=f"event_join_{ev_id}")]
            ])
        if photo:
            await message.answer_photo(photo, caption=text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("event_join_"))
async def event_join(callback: CallbackQuery, state: FSMContext):
    ev_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered, fio, group_name FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    if not res or res[0] == 0:
        await callback.answer("Сначала пройдите регистрацию (/start)", show_alert=True)
        return
        
    await state.update_data(event_id=ev_id)
    await state.set_state(EventApplyState.skill)
    await callback.message.answer("Что вы умеете делать для этого мероприятия? (Напишите коротко навык):")

@router.message(EventApplyState.skill)
async def event_save_apply(message: Message, state: FSMContext):
    if check_bad_words(message.text):
        await message.answer("⚠️ Нецензурная лексика запрещена. Напишите навык заново:")
        return
        
    data = await state.get_data()
    user_id = message.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    fio, group = user
    
    cursor.execute(
        "INSERT INTO event_applications (event_id, user_id, fio, group_name, skill) VALUES (?, ?, ?, ?, ?)",
        (data['event_id'], user_id, fio, group, message.text)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ваша заявка отправлена организаторам!")
    await state.clear()

@router.message(F.text.in_(["💡 Идеи для колледжа", "💡 Колледж идеялары"]))
async def idea_menu(message: Message, state: FSMContext):
    day = date.today().day
    if day not in [10, 20]:
        await message.answer("💡 Идеи можно отправлять **только 10-го и 20-го числа** каждого месяца!")
        return
        
    user_id = message.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if not res or res[0] == 0:
        conn.close()
        await message.answer("⚠️ Требуется регистрация (/start).")
        return
        
    today_str = date.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM ideas WHERE user_id = ? AND timestamp LIKE ?", (user_id, f"{today_str}%"))
    count = cursor.fetchone()[0]
    conn.close()
    
    if count >= 2:
        await message.answer("⚠️ Вы уже исчерпали лимит в 2 идеи на сегодня.")
        return
        
    await state.set_state(IdeaState.text)
    await message.answer("💡 Напишите вашу идею для колледжа следующим сообщением:")

@router.message(IdeaState.text)
async def idea_submit(message: Message, state: FSMContext):
    if check_bad_words(message.text):
        await message.answer("⚠️ В тексте обнаружен мат. Исправьте текст идеи:")
        return
        
    user_id = message.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    fio, group = user
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO ideas (user_id, fio, group_name, text, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, fio, group, message.text, timestamp)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ваша идея принята и отправлена администрации!")
    await state.clear()

@router.message(F.text.in_(["📊 Опросы", "📊 Сауалнамалар"]))
async def show_polls(message: Message):
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, question, options FROM polls WHERE active = 1")
    polls = cursor.fetchall()
    conn.close()
    
    if not polls:
        await message.answer("📊 Активных опросов пока нет.")
        return
        
    for p_id, quest, opts in polls:
        options_list = opts.split(";")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=opt, callback_data=f"poll_{p_id}_{opt}")] for opt in options_list
        ])
        await message.answer(f"📊 **Опрос:**\n{quest}", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("poll_"))
async def poll_vote(callback: CallbackQuery):
    parts = callback.data.split("_")
    p_id = int(parts[1])
    answer = "_".join(parts[2:])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    fio = user[0] if user else "Гость"
    group = user[1] if user else "-"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO poll_answers (poll_id, user_id, fio, group_name, answer, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (p_id, user_id, fio, group, answer, timestamp)
    )
    conn.commit()
    conn.close()
    
    await callback.answer("✅ Ваш голос учтен!", show_alert=True)
    await callback.message.edit_text(f"📊 Спасибо за участие! Ваш ответ: *{answer}*", parse_mode="Markdown")

@router.message(F.text.in_(["📞 Прямая связь", "📞 Тікелей байланыс"]))
async def direct_contact(message: Message):
    text = (
        "📞 **Прямая связь с колледжем:**\n\n"
        "🏫 Приемная: каб. 101\n"
        "🏛 Дирекция: каб. 205\n"
        "📋 Отдел кадров: каб. 103\n\n"
        "⚠️ *Внимание!* Вы можете отправить официальное обращение администрации (не более 1 раза в неделю)."
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✉️ Подать обращение", callback_data="make_appeal")]
    ])
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "make_appeal")
async def start_appeal(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT registered FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    
    if not res or res[0] == 0:
        conn.close()
        await callback.message.answer("⚠️ Для подачи обращения требуется регистрация.")
        return
        
    cursor.execute("SELECT timestamp FROM appeals WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    last = cursor.fetchone()
    if last:
        last_date = datetime.strptime(last[0], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_date).days < 7:
            conn.close()
            await callback.message.answer("⚠️ Вы можете подавать обращение только 1 раз в неделю!")
            return
            
    conn.close()
    await state.set_state(AppealState.text)
    await callback.message.answer("✉️ Опишите ваше обращение/ошибку подробно:")

@router.message(AppealState.text)
async def save_appeal(message: Message, state: FSMContext):
    if check_bad_words(message.text):
        await message.answer("⚠️ В обращении обнаружена нецензурная лексика. Перепишите текст:")
        return
        
    user_id = message.from_user.id
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    fio, group = user
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO appeals (user_id, fio, group_name, text, timestamp) VALUES (?, ?, ?, ?, ?)",
        (user_id, fio, group, message.text, timestamp)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Ваше обращение зарегистрировано и передано администрации.")
    await state.clear()

@router.message(F.text.in_(["🔐 Админка", "🔐 Әкімшілік"]))
async def admin_auth_start(message: Message, state: FSMContext):
    await state.set_state(AdminAuthState.password)
    await message.answer("🔑 Введите пароль администратора:")

@router.message(AdminAuthState.password)
async def admin_check_password(message: Message, state: FSMContext):
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_pass'")
    real_pass = cursor.fetchone()[0]
    conn.close()
    
    try:
        await message.delete()
    except:
        pass
        
    if message.text.strip() == real_pass:
        await state.clear()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🍽 Добавить меню", callback_data="adm_menu"),
             InlineKeyboardButton(text="🍲 Управление блюдами", callback_data="adm_dishes")],
            [InlineKeyboardButton(text="⭐ Отзывы", callback_data="adm_reviews"),
             InlineKeyboardButton(text="📅 Изменить расписание", callback_data="adm_schedule")],
            [InlineKeyboardButton(text="🎉 Добавить мероприятие", callback_data="adm_event"),
             InlineKeyboardButton(text="💡 Идеи колледжа", callback_data="adm_ideas")],
            [InlineKeyboardButton(text="📊 Опросы", callback_data="adm_polls"),
             InlineKeyboardButton(text="✉️ Обращения", callback_data="adm_appeals")],
            [InlineKeyboardButton(text="📢 Оповещение", callback_data="adm_broadcast"),
             InlineKeyboardButton(text="🔑 Изменить пароль", callback_data="adm_changepass")]
        ])
        await message.answer("✅ Успешный вход в панель администратора:", reply_markup=keyboard)
    else:
        await message.answer("❌ Неверный пароль!")
        await state.clear()

@router.callback_query(F.data == "adm_changepass")
async def adm_changepass_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminChangePass.old_pass)
    await callback.message.answer("🔑 Введите старый пароль администратора:")

@router.message(AdminChangePass.old_pass)
async def adm_changepass_old(message: Message, state: FSMContext):
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'admin_pass'")
    real_pass = cursor.fetchone()[0]
    conn.close()
    
    if message.text.strip() != real_pass:
        await message.answer("❌ Неверный старый пароль.")
        await state.clear()
        return
        
    await state.set_state(AdminChangePass.new_pass1)
    await message.answer("🔑 Введите новый пароль:")

@router.message(AdminChangePass.new_pass1)
async def adm_changepass_new1(message: Message, state: FSMContext):
    await state.update_data(new_pass=message.text.strip())
    await state.set_state(AdminChangePass.new_pass2)
    await message.answer("🔑 Повторите новый пароль для подтверждения:")

@router.message(AdminChangePass.new_pass2)
async def adm_changepass_new2(message: Message, state: FSMContext):
    data = await state.get_data()
    if message.text.strip() != data["new_pass"]:
        await message.answer("❌ Пароли не совпадают. Изменение отменено.")
        await state.clear()
        return
        
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'admin_pass'", (data["new_pass"],))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Пароль администратора успешно изменен!")
    await state.clear()

@router.callback_query(F.data == "adm_menu")
async def adm_menu_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminAddMenu.text)
    await callback.message.answer("🍽 Отправьте текст меню на сегодня:")

@router.message(AdminAddMenu.text)
async def adm_menu_save(message: Message, state: FSMContext):
    today = date.today().strftime("%Y-%m-%d")
    text_content = message.text
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO daily_menu (menu_date, category, dish_text) VALUES (?, ?, ?)", (today, "Общее меню", text_content))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Меню на сегодня успешно опубликовано!")
    await state.clear()

@router.callback_query(F.data == "adm_dishes")
async def adm_dishes_menu(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить блюдо", callback_data="adm_add_dish_start")],
        [InlineKeyboardButton(text="📋 Список всех блюд", callback_data="adm_list_dishes")]
    ])
    await callback.message.answer("🍲 Управление базой блюд:", reply_markup=keyboard)

@router.callback_query(F.data == "adm_add_dish_start")
async def adm_add_dish(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminAddDish.name)
    await callback.message.answer("Введите название блюда:")

@router.message(AdminAddDish.name)
async def adm_dish_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminAddDish.category)
    await message.answer("Введите категорию (Суп, Второе, Салат и т.д.):")

@router.message(AdminAddDish.category)
async def adm_dish_cat(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await state.set_state(AdminAddDish.grams)
    await message.answer("Введите вес порции в граммах (число):")

@router.message(AdminAddDish.grams)
async def adm_dish_grams(message: Message, state: FSMContext):
    await state.update_data(grams=message.text)
    await state.set_state(AdminAddDish.kbzh)
    await message.answer("Введите КБЖУ (например, 250 ккал):")

@router.message(AdminAddDish.kbzh)
async def adm_dish_kbzh(message: Message, state: FSMContext):
    await state.update_data(kbzh=message.text)
    await state.set_state(AdminAddDish.allergens)
    await message.answer("Введите аллергены (или нет):")

@router.message(AdminAddDish.allergens)
async def adm_dish_all(message: Message, state: FSMContext):
    await state.update_data(allergens=message.text)
    await state.set_state(AdminAddDish.ingredients)
    await message.answer("Введите состав блюда:")

@router.message(AdminAddDish.ingredients)
async def adm_dish_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dishes (name, category, portion_grams, kbzh, allergens, ingredients) VALUES (?, ?, ?, ?, ?, ?)",
        (data['name'], data['category'], int(data.get('grams', 0)), data['kbzh'], data['allergens'], message.text)
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Блюдо успешно добавлено в базу!")
    await state.clear()

@router.callback_query(F.data == "adm_list_dishes")
async def adm_list_dishes(callback: CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM dishes")
    dishes = cursor.fetchall()
    conn.close()
    
    if not dishes:
        await callback.message.answer("Блюд нет.")
        return
        
    text = "🍲 **Список блюд:**\n"
    for d_id, name in dishes:
        text += f"▪️ ID {d_id}: {name}\n"
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "adm_reviews")
async def adm_reviews(callback: CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT fio, group_name, rating, text, timestamp FROM reviews ORDER BY rating DESC")
    reviews = cursor.fetchall()
    conn.close()
    
    if not reviews:
        await callback.message.answer("⭐ Отзывов нет.")
        return
        
    text = "⭐ **Все отзывы:**\n\n"
    for fio, group, rating, rev_text, timestamp in reviews:
        text += f"👤 {fio} ({group})\n⭐ Оценка: {rating}/10\n💬 {rev_text}\n📅 {timestamp}\n-------------------\n"
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "adm_schedule")
async def adm_schedule_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminSchedule.content)
    await callback.message.answer("📅 Отправьте новое расписание (текст или фото):")

@router.message(AdminSchedule.content)
async def adm_schedule_save(message: Message, state: FSMContext):
    link = message.text or message.caption or ""
    photo_id = message.photo[-1].file_id if message.photo else None
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO schedule (link, photo_id) VALUES (?, ?)", (link, photo_id))
    conn.commit()
    conn.close()
    
    await message.answer("✅ Расписание обновлено!")
    await state.clear()

@router.callback_query(F.data == "adm_event")
async def adm_event_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminEvent.photo)
    await callback.message.answer("🎉 Отправьте фото для мероприятия (или '-'):")

@router.message(AdminEvent.photo)
async def adm_event_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id if message.photo else None
    await state.update_data(photo=photo_id)
    await state.set_state(AdminEvent.title)
    await message.answer("Введите текст/описание мероприятия:")

@router.message(AdminEvent.title)
async def adm_event_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminEvent.need_people)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="need_yes"),
         InlineKeyboardButton(text="Нет", callback_data="need_no")]
    ])
    await message.answer("Нужен ли набор студентов (кнопка участия)?", reply_markup=keyboard)

@router.callback_query(F.data.startswith("need_"))
async def adm_event_need(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    need = 1 if callback.data == "need_yes" else 0
    await state.update_data(need_people=need)
    await state.set_state(AdminEvent.date)
    await message.answer("Укажите дату проведения (например, 15.11.2026):")

@router.message(AdminEvent.date)
async def adm_event_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await state.set_state(AdminEvent.location)
    await message.answer("Укажите место проведения:")

@router.message(AdminEvent.location)
async def adm_event_location(message: Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO events (title_text, photo_id, event_date, location, need_students) VALUES (?, ?, ?, ?, ?)",
        (data['title'], data['photo'], data['date'], message.text, data['need_people'])
    )
    conn.commit()
    conn.close()
    
    await message.answer("✅ Мероприятие успешно создано и опубликовано!")
    await state.clear()

@router.callback_query(F.data == "adm_ideas")
async def adm_ideas_list(callback: CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, fio, group_name, text, timestamp FROM ideas WHERE status = 'pending'")
    ideas = cursor.fetchall()
    conn.close()
    
    if not ideas:
        await callback.message.answer("💡 Новых идей нет.")
        return
        
    for i_id, fio, group, text, ts in ideas:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"idea_acc_{i_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"idea_rej_{i_id}")]
        ])
        await callback.message.answer(f"💡 **Идея от {fio} ({group})**\n📅 {ts}\n\n{text}", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("idea_"))
async def idea_decision(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    i_id = int(parts[2])
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM ideas WHERE id = ?", (i_id,))
    res = cursor.fetchone()
    
    if res:
        u_id = res[0]
        if action == "acc":
            cursor.execute("UPDATE ideas SET status = 'accepted' WHERE id = ?", (i_id,))
            conn.commit()
            await bot.send_message(u_id, "✅ Ваша идея принята во внимание администрацией!")
            await callback.answer("Идея принята!")
        else:
            cursor.execute("UPDATE ideas SET status = 'rejected' WHERE id = ?", (i_id,))
            conn.commit()
            await bot.send_message(u_id, "❌ Ваша идея не принята.")
            await callback.answer("Идея отклонена.")
    conn.close()
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data == "adm_polls")
async def adm_polls_menu(callback: CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, question FROM polls")
    polls = cursor.fetchall()
    conn.close()
    
    text = "📊 **Список опросов:**\n"
    for p_id, q in polls:
        text += f"▪️ #{p_id}: {q}\n"
    await callback.message.answer(text, parse_mode="Markdown")

@router.callback_query(F.data == "adm_appeals")
async def adm_appeals_list(callback: CallbackQuery):
    await callback.answer()
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, fio, group_name, text, timestamp FROM appeals WHERE status = 'unread'")
    appeals = cursor.fetchall()
    conn.close()
    
    if not appeals:
        await callback.message.answer("✉️ Новых обращений нет.")
        return
        
    for a_id, u_id, fio, group, text, ts in appeals:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Прочитано", callback_data=f"appeal_read_{a_id}_{u_id}")]
        ])
        await callback.message.answer(f"✉️ **Обращение от {fio} ({group})**\n📅 {ts}\n\n{text}", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("appeal_read_"))
async def appeal_read(callback: CallbackQuery):
    parts = callback.data.split("_")
    a_id = int(parts[2])
    u_id = int(parts[3])
    
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE appeals SET status = 'read' WHERE id = ?", (a_id,))
    conn.commit()
    conn.close()
    
    await bot.send_message(u_id, "✅ Ваше обращение прочитано и рассмотрено администрацией!")
    await callback.answer("Отмечено как прочитанное!")
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data == "adm_broadcast")
async def adm_broadcast_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AdminBroadcast.text)
    await callback.message.answer("📢 Введите текст срочного оповещения для всех пользователей:")

@router.message(AdminBroadcast.text)
async def adm_broadcast_send(message: Message, state: FSMContext):
    text = f"📢 **СРОЧНОЕ ОПОВЕЩЕНИЕ:**\n\n{message.text}"
    conn = sqlite3.connect("college_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    count = 0
    for u in users:
        try:
            await bot.send_message(u[0], text, parse_mode="Markdown")
            count += 1
        except:
            pass
            
    await message.answer(f"✅ Оповещение успешно отправлено {count} пользователям!")
    await state.clear()

async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    while True:
        await asyncio.sleep(3600)

async def main():
    init_db()
    dp.include_router(router)
    asyncio.create_task(web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
    

