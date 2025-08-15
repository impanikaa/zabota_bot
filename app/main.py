import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers import user
from app.handlers import admin
from app.db.session import Session
from app.db.models import User
from app.keyboards import get_main_menu, get_support_menu
from app.db import init_db
from app.config import BOT_TOKEN
from app.utils.roles import get_user_role

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    session = Session()
    user_id = message.from_user.id
    is_new = False
    role = get_user_role(user_id)

    if not session.query(User).filter_by(user_id=user_id).first():
        session.add(User(user_id=user_id))
        session.commit()
        is_new = True

    await message.answer(
        "Привет! Я бот проекта «Заботать!» — психологическая поддержка для олимпиадников 💛\n\nВыбирай нужный раздел в меню ниже.",
        reply_markup=get_main_menu(role)
    )

    if is_new:
        await asyncio.sleep(0.3)
        markup = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Заполнить анкету", callback_data="fill_profile")]
            ]
        )
        await bot.send_message(
            chat_id=message.chat.id,
            text="Хочешь сразу заполнить анкету?",
            reply_markup=markup
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
    role = get_user_role(message.from_user.id)
    await message.answer("Главное меню:", reply_markup=get_main_menu(role))

@dp.message(F.text == "/myid")
async def get_my_id(message: Message):
    await message.answer(f"Твой user_id: {message.from_user.id}\nТвой username: @{message.from_user.username or 'нет'}")

async def main():
    init_db()
    print("Бот запускается...")
    dp.include_router(user.router)
    dp.include_router(admin.router)
    await dp.start_polling(bot)
    print("Бот запущен!")

if __name__ == "__main__":
    asyncio.run(main())
