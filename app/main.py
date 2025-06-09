import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from handlers import user
from db.session import Session
from db.models import User

from app.db import init_db
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    session = Session()
    user_id = message.from_user.id

    if not session.query(User).filter_by(user_id=user_id).first():
        session.add(User(user_id=user_id))
        session.commit()

    await message.answer(
        "Привет! Я бот проекта «Заботать!» — психологическая поддержка для олимпиадников 💛\n\nВыбирай нужный раздел в меню ниже.",
        reply_markup=get_main_menu()
    )


@dp.message(lambda m: m.text == "📚 Библиотека")
async def handle_library(message: Message):
    await message.answer("📚 В будущем здесь будет библиотека статей. Пока она в разработке!")

@dp.message(lambda m: m.text == "⏰ Напоминания")
async def handle_reminders(message: Message):
    await message.answer("⏰ Здесь можно будет настроить напоминания. Скоро будет доступно!")

@dp.message(lambda m: m.text == "💬 Поддержка")
async def handle_support(message: Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🙏 #болталка")],
            [KeyboardButton(text="📝 Отзыв")],
            [KeyboardButton(text="❓ Вопрос администрации")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Вот, что могу предложить для поддержки:", reply_markup=markup)

@dp.message(lambda m: m.text == "ℹ️ О проекте")
async def handle_about(message: Message):
    await message.answer("ℹ️ «Заботать!» — проект психологической поддержки олимпиадников. Подробнее: https://zabota-olymp.ru")

@dp.message(lambda m: m.text == "⬅️ Назад")
async def handle_back(message: Message):
    await message.answer("Главное меню:", reply_markup=get_main_menu())

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Библиотека")],
            [KeyboardButton(text="⏰ Напоминания")],
            [KeyboardButton(text="💬 Поддержка")],
            [KeyboardButton(text="ℹ️ О проекте")],
        ],
        resize_keyboard=True
    )

def get_support_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

async def main():
    init_db()
    print("Бот запускается...")
    dp.include_router(user.router)
    await dp.start_polling(bot)
    print("Бот запущен!")

if __name__ == "__main__":
    asyncio.run(main())
