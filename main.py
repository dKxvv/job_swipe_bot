"""
Job Swipe Bot — бот для поиска IT-вакансий в стиле "свайпов"
Версия: 1.0 (базовый MVP)
"""
import asyncpg
import asyncio
import os
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class ProfileState(StatesGroup):
    waiting_skills = State()
    waiting_experience = State()
    waiting_salary = State()
    waiting_format = State()


# ===== СОСТОЯНИЯ ДЛЯ СВАЙПОВ (будет использоваться позже) =====
class SwipeState(StatesGroup):
    viewing_vacancy = State()

# ============ ШАГ 1: ИНИЦИАЛИЗАЦИЯ ============

# Для корректной работы на Windows (фиксим ошибку с событиями)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Загружаем переменные из .env файла
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен существует
if not BOT_TOKEN:
    print("❌ ОШИБКА: Не найден BOT_TOKEN в файле .env")
    print("👉 Создайте файл .env в корне проекта со строкой:")
    print('   BOT_TOKEN=ваш_токен_от_BotFather')
    print("\nПример правильного файла .env:")
    print("   BOT_TOKEN=123456789:AAH_ABC123xyz_this_is_secret")
    sys.exit(1)

# Инициализируем бота и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()


# Подключение к БД
async def init_db():
    global db_pool
    try:
        # Пробуем подключиться
        db_pool = await asyncpg.create_pool(
            user='postgres',
            password='790731',
            database='job_swipe_bot',
            host='127.0.0.1',
            port=5432,
            min_size=1,
            max_size=10,
            command_timeout=60
        )
        print("✅ База данных подключена!")
        return db_pool
    except asyncpg.exceptions.InvalidPasswordError:
        print("❌ ОШИБКА: Неверный пароль от PostgreSQL!")
        print("👉 Проверьте пароль в коде (строка с password='...')")
        print("👉 Или сбросьте пароль через pg_hba.conf (см. инструкцию выше)")
        sys.exit(1)
    except asyncpg.exceptions.ConnectionDoesNotExistError:
        print("❌ ОШИБКА: Сервер PostgreSQL не запущен!")
        print("👉 Откройте 'Службы Windows' → найдите 'postgresql-x64-17' → запустите")
        sys.exit(1)
    except asyncpg.exceptions.InvalidCatalogNameError:
        print("❌ ОШИБКА: База данных 'job_swipe_bot' не существует!")
        print("👉 Создайте базу в pgAdmin: Databases → ПКМ → Create → Database")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неизвестная ошибка подключения к БД: {e}")
        sys.exit(1)
# Глобальная переменная для пула подключений
db_pool = None


# ============ ШАГ 2: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===========
async def get_user_from_db(telegram_id: int):
    """Получаем профиль пользователя из БД"""
    async with db_pool.acquire() as conn:
        return await conn.fetchrow(
            'SELECT * FROM users WHERE telegram_id = $1',
            telegram_id
        )

async def get_next_vacancy(user_skills: list):
    """Получаем следующую вакансию (пока тестовую)"""
    # Позже заменим на запрос к таблице vacancies
    return {
        "id": 1,
        "title": "Python Developer",
        "company": "IT Startups Inc.",
        "salary": 150000,
        "location": "Москва (удалёнка)",
        "skills": ["python", "django", "postgres"],
        "url": "https://example.com/vacancy/1"
    }

async def save_response(user_id: int, vacancy_id: int, action: str):
    """Сохраняем отклик пользователя (пока просто логируем)"""
    print(f"📝 Отклик: пользователь {user_id} -> вакансия {vacancy_id} -> действие: {action}")
    # Позже добавим сохранение в таблицу responses

# ============ ШАГ 3: ОБРАБОТЧИКИ КОМАНД ============

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    welcome_text = (
        f"👋 Привет, {user.first_name}!\n\n"
        "Я — бот для поиска IT-вакансий в стиле свайпов ❤️/⏭\n\n"
        "✨ Как это работает:\n"
        "1. Заполни профиль (навыки, опыт, зарплата)\n"
        "2. Получай карточки вакансий\n"
        "3. Свайпай: ❤️ — интересно, ⏭ — пропустить\n"
        "4. После лайка — отправляй отклик компании\n\n"
        "👉 Начни с команды /profile чтобы рассказать о себе!"
    )
    await message.answer(welcome_text, parse_mode=ParseMode.HTML)

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "/start — приветствие и инструкция\n"
        "/help — эта справка\n"
        "/profile — заполнить профиль ✅\n"
        "/myprofile — посмотреть свой профиль ✅\n"
        "/search — искать вакансии (скоро) 🔜"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    await state.set_state(ProfileState.waiting_skills)
    await message.answer(
        "🛠️ Давайте заполним ваш профиль!\n\n"
        "👉 Напишите через запятую ваши навыки (например: Python, Django, PostgreSQL)\n"
        "Пример: <code>Python, React, Docker</code>",
        parse_mode=ParseMode.HTML
    )

@router.message(ProfileState.waiting_skills)
async def process_skills(message: Message, state: FSMContext):
    skills_text = message.text.strip()
    skills = [skill.strip().lower() for skill in skills_text.split(",") if skill.strip()]
    
    if len(skills) < 2:
        await message.answer(
            "❌ Укажите минимум 2 навыка через запятую.\n"
            "Пример: <code>Python, SQL</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    await state.update_data(skills=skills)
    await state.set_state(ProfileState.waiting_experience)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Junior (< 1 года)", callback_data="exp_junior")],
        [InlineKeyboardButton(text="Middle (1-3 года)", callback_data="exp_middle")],
        [InlineKeyboardButton(text="Senior (3+ года)", callback_data="exp_senior")]
    ])
    
    await message.answer("👉 Выберите ваш уровень опыта:", reply_markup=kb)

@router.callback_query(F.data.startswith("exp_"))
async def process_experience(callback: CallbackQuery, state: FSMContext):
    exp_map = {
        "exp_junior": "Junior",
        "exp_middle": "Middle",
        "exp_senior": "Senior"
    }
    experience = exp_map.get(callback.data, "Middle")
    
    await state.update_data(experience=experience)
    await state.set_state(ProfileState.waiting_salary)
    
    await callback.message.edit_text(
        "👉 Укажите желаемую зарплату в ₽ (только число):\n"
        "Пример: <code>150000</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.message(ProfileState.waiting_salary)
async def process_salary(message: Message, state: FSMContext):
    try:
        salary = int(message.text.replace(" ", "").replace("₽", ""))
        if salary < 10000:
            await message.answer(
                "❌ Слишком низкая зарплата. Укажите реалистичную сумму (от 10 000 ₽)",
                parse_mode=ParseMode.HTML
            )
            return
    except ValueError:
        await message.answer(
            "❌ Введите только число. Пример: <code>150000</code>",
            parse_mode=ParseMode.HTML
        )
        return
    
    await state.update_data(salary=salary)
    await state.set_state(ProfileState.waiting_format)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Офис", callback_data="format_office")],
        [InlineKeyboardButton(text="🌍 Удалёнка", callback_data="format_remote")],
        [InlineKeyboardButton(text="🔀 Гибрид", callback_data="format_hybrid")]
    ])
    
    await message.answer("👉 Выберите формат работы:", reply_markup=kb)

@router.callback_query(F.data.startswith("format_"))
async def process_format(callback: CallbackQuery, state: FSMContext):
    format_map = {
        "format_office": "Офис",
        "format_remote": "Удалёнка",
        "format_hybrid": "Гибрид"
    }
    work_format = format_map.get(callback.data, "Удалёнка")
    
    data = await state.get_data()
    skills = ", ".join(data["skills"])
    
    # Формируем ответ
    response = (
        "✅ Профиль заполнен!\n\n"
        f"🛠️ Навыки: {skills}\n"
        f"💼 Опыт: {data['experience']}\n"
        f"💰 Зарплата: {data['salary']} ₽\n"
        f"📍 Формат: {work_format}\n\n"
        "Теперь нажмите /myprofile чтобы посмотреть свой профиль!"
    )
    
    # Сохраняем в БД
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO users (telegram_id, skills, experience, salary, work_format)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (telegram_id) DO UPDATE SET
                        skills = $2,
                        experience = $3,
                        salary = $4,
                        work_format = $5,
                        created_at = NOW()
                ''', callback.from_user.id, data["skills"], data['experience'], data['salary'], work_format)
            print(f"✅ Профиль пользователя {callback.from_user.id} сохранён в БД")
        except Exception as e:
            print(f"❌ Ошибка сохранения в БД: {e}")
    
    await state.clear()
    await callback.message.edit_text(response)
    await callback.answer()

@router.message(Command("myprofile"))
async def cmd_myprofile(message: Message):
    if not db_pool:
        await message.answer("❌ База данных недоступна")
        return
    
    try:
        user = await get_user_from_db(message.from_user.id)
        
        if not user:
            await message.answer("❌ Сначала заполните профиль через /profile")
            return
        
        response = (
            "👤 <b>Ваш профиль:</b>\n\n"
            f"🛠️ Навыки: {', '.join(user['skills'])}\n"
            f"💼 Опыт: {user['experience']}\n"
            f"💰 Зарплата: {user['salary']} ₽\n"
            f"📍 Формат: {user['work_format']}"
        )
        await message.answer(response, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        print(f"❌ Ошибка при получении профиля: {e}")
        await message.answer("❌ Ошибка при загрузке профиля. Попробуйте позже.")

@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext):
    """Показываем первую вакансию (тестовую)"""
    user = await get_user_from_db(message.from_user.id)
    
    if not user:
        await message.answer("❌ Сначала заполните профиль через /profile")
        return
    
    vacancy = await get_next_vacancy(user["skills"])
    
    # Сохраняем вакансию в состояние
    await state.set_state(SwipeState.viewing_vacancy)
    await state.update_data(current_vacancy=vacancy)
    
    # Отправляем карточку
    await message.answer(
        f"💼 <b>{vacancy['title']}</b>\n"
        f"🏢 {vacancy['company']}\n"
        f"💰 {vacancy['salary']} ₽\n"
        f"📍 {vacancy['location']}\n\n"
        f"Требуемые навыки: {', '.join(vacancy['skills'])}",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❤️ Подходит", callback_data="like")],
            [InlineKeyboardButton(text="⏭ Пропустить", callback_data="skip")]
        ])
    )

@router.callback_query(F.data == "like")
async def handle_like(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    vacancy = data.get("current_vacancy")
    
    if not vacancy:
        await callback.answer("❌ Вакансия не найдена", show_alert=True)
        return
    
    # Сохраняем отклик
    await save_response(callback.from_user.id, vacancy["id"], "like")
    
    # Показываем следующую вакансию
    await callback.message.edit_text(
        f"✅ Отклик отправлен!\nКомпания свяжется с вами по ссылке:\n{vacancy['url']}",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "skip")
async def handle_skip(callback: CallbackQuery, state: FSMContext):
    # Просто очищаем состояние
    await state.clear()
    await callback.message.edit_text("⏭ Вакансия пропущена", reply_markup=None)
    await callback.answer()

@router.message(F.text)
async def handle_any_text(message: Message):
    await message.answer(
        "💬 Я понимаю команды:\n"
        "/start — приветствие\n"
        "/help — справка\n"
        "/profile — заполнить профиль ✅\n"
        "/myprofile — посмотреть профиль ✅\n"
        "/search — искать вакансии 🔜"
    )

# ============ ШАГ 4: ЗАПУСК БОТА ============

async def main():
    global db_pool
    await init_db()
    
    # Создаём таблицы при старте
    async with db_pool.acquire() as conn:
        # Таблица пользователей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                skills TEXT[],
                experience VARCHAR(20),
                salary INTEGER,
                work_format VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        # Таблица откликов (для будущего)
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS responses (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                vacancy_id INTEGER NOT NULL,
                action VARCHAR(10) NOT NULL,  -- 'like' или 'skip'
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
    
    dp.include_router(router)
    
    print("=" * 50)
    print("✅ Job Swipe Bot запущен!")
    print("✅ База данных подключена!")
    print("👉 Бот готов принимать сообщения")
    print("👉 Нажмите Ctrl+C чтобы остановить")
    print("=" * 50)
    
    await dp.start_polling(bot)


# ============ ТОЧКА ВХОДА ============

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")