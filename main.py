"""
Job Swipe Bot — бот для поиска IT-вакансий в стиле "свайпов"
Версия: 1.0 (базовый MVP)
"""

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

# ============ ШАГ 1: ИНИЦИАЛИЗАЦИЯ ============

# Для корректной работы на Windows (фиксим ошибку с событиями)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Загружаем переменные из .env файла
load_dotenv()
print(f"✅ Загружен токен: {os.getenv('BOT_TOKEN')[:20]}...")

# Получаем токен бота
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

# ============ ШАГ 2: ОБРАБОТЧИКИ КОМАНД ============

@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
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
    """Обработчик команды /help"""
    help_text = (
        "📚 <b>Доступные команды:</b>\n\n"
        "/start — приветствие и инструкция\n"
        "/help — эта справка\n"
        "/profile — заполнить/изменить профиль (скоро)\n"
        "/search — начать поиск вакансий (скоро)\n\n"
        "💡 Бот в разработке. Первые вакансии появятся через 2-3 дня!"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    """Начало заполнения профиля"""
    await state.set_state(ProfileState.waiting_skills)
    await message.answer(
        "🛠️ Давайте заполним ваш профиль!\n\n"
        "1. Напишите через запятую ваши навыки (например: Python, Django, PostgreSQL)\n"
        "Пример: Python, React, Docker",
        parse_mode=ParseMode.HTML
    )

@router.message(ProfileState.waiting_skills)
async def process_skills(message: Message, state: FSMContext):
    skills_text = message.text.strip()
    skills = [skill.strip().lower() for skill in skills_text.split(",") if skill.strip()]
    
    if len(skills) < 2:
        await message.answer("❌ Укажите минимум 2 навыка через запятую.\nПример: <code>Python, SQL</code>", parse_mode=ParseMode.HTML)
        return
    
    await state.update_data(skills=skills)
    await state.set_state(ProfileState.waiting_experience)
    
    # Кнопки для выбора опыта
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Junior (< 1 года)", callback_data="exp_junior")],
        [InlineKeyboardButton(text="Middle (1-3 года)", callback_data="exp_middle")],
        [InlineKeyboardButton(text="Senior (3+ года)", callback_data="exp_senior")]
    ])
    
    await message.answer(
        "👉 Выберите ваш уровень опыта:",
        reply_markup=kb
    )
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

# ===== ОБРАБОТКА ЗАРПЛАТЫ =====
@router.message(ProfileState.waiting_salary)
async def process_salary(message: Message, state: FSMContext):
    try:
        salary = int(message.text.replace(" ", "").replace("₽", ""))
        if salary < 30000:
            await message.answer("❌ Слишком низкая зарплата. Укажите реалистичную сумму (от 30 000 ₽)")
            return
    except ValueError:
        await message.answer("❌ Введите только число. Пример: <code>150000</code>", parse_mode=ParseMode.HTML)
        return
    
    await state.update_data(salary=salary)
    await state.set_state(ProfileState.waiting_format)
    
    # Кнопки для формата работы
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Офис", callback_data="format_office")],
        [InlineKeyboardButton(text="🌍 Удалёнка", callback_data="format_remote")],
        [InlineKeyboardButton(text="🔀 Гибрид", callback_data="format_hybrid")]
    ])
    
    await message.answer(
        "👉 Выберите формат работы:",
        reply_markup=kb
    )

# ===== ОБРАБОТКА ФОРМАТА РАБОТЫ =====
@router.callback_query(F.data.startswith("format_"))
async def process_format(callback: CallbackQuery, state: FSMContext):
    format_map = {
        "format_office": "Офис",
        "format_remote": "Удалёнка",
        "format_hybrid": "Гибрид"
    }
    work_format = format_map.get(callback.data, "Удалёнка")
    
    # Получаем все данные профиля
    data = await state.get_data()
    skills = ", ".join(data["skills"])
    
    # Формируем ответ
    response = (
        "✅ Профиль заполнен!\n\n"
        f"🛠️ Навыки: {skills}\n"
        f"💼 Опыт: {data['experience']}\n"
        f"💰 Зарплата: {data['salary']} ₽\n"
        f"📍 Формат: {work_format}\n\n"
        "Теперь нажмите /search чтобы начать поиск вакансий!"
    )
    
    await state.clear()
    await callback.message.edit_text(response)
    await callback.answer()


@router.message(Command("search"))
async def cmd_search(message: Message):
    """Заглушка для команды /search (будет реализована позже)"""
    await message.answer(
        "🔍 Поиск вакансий временно недоступен.\n"
        "Первые вакансии появятся в боте через несколько дней!\n"
        "А пока — следите за обновлениями в нашем канале: @job_swipe_news"
    )

# ============ ШАГ 3: ОБРАБОТКА ЛЮБОГО ТЕКСТА ============

@router.message(F.text)
async def handle_any_text(message: Message):
    """Ответ на любой текстовый запрос пользователя"""
    await message.answer(
        "💬 Я понимаю только команды:\n"
        "/start — начать работу\n"
        "/help — справка\n"
        "/profile — мой профиль (скоро)\n"
        "/search — искать вакансии (скоро)\n\n"
        "Или просто жди обновлений — скоро будет круто! 🚀"
    )

# ============ ШАГ 4: ЗАПУСК БОТА ============

async def main():
    """Основная функция запуска бота"""
    # Регистрируем роутер
    dp.include_router(router)
    
    # Информируем о запуске
    print("=" * 50)
    print("✅ Job Swipe Bot запущен!")
    print("👉 Бот готов принимать сообщения")
    print("👉 Нажмите Ctrl+C чтобы остановить")
    print("=" * 50)
    
    # Запускаем опрос обновлений от Telegram
    await dp.start_polling(bot)

# ============ ТОЧКА ВХОДА ============

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        print("Проверьте:")
        print("  1. Правильность токена в .env")
        print("  2. Доступ к интернету")
        print("  3. Не заблокирован ли ваш IP Telegram")