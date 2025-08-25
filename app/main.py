import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
import logging

from app.handlers import user, admin, broadcast, superadmin
from app.services import (library, library_admin, feedback, feedback_admin, chat, chat_admin, question,
                          question_admin, reminders_admin, reminders)
from app.db.session import Session
from app.db.models import User
from app.keyboards import get_main_menu
from app.db import init_db
from app.config import BOT_TOKEN
from app.utils.roles import get_user_role

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    session = Session()
    user_id = message.from_user.id
    is_new = False
    role = get_user_role(user_id)

    if user_id != bot.id and not session.query(User).filter_by(user_id=user_id).first():
        session.add(User(user_id=user_id, role=0))
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
    await message.answer(
        "ℹ️ «Заботать!» — проект психологической поддержки олимпиадников. Подробнее: https://zabota-olymp.ru")


@dp.message(lambda m: m.text == "⬅️ Назад")
async def handle_back(message: Message):
    role = get_user_role(message.from_user.id)
    await message.answer("Главное меню:", reply_markup=get_main_menu(role))


@dp.message(F.text == "/myid")
async def get_my_id(message: Message):
    await message.answer(f"Твой user_id: {message.from_user.id}\nТвой username: @{message.from_user.username or 'нет'}")


@dp.message(F.text == "/check_scheduler")
async def check_scheduler(message: Message):
    """Проверка состояния планировщика"""
    from app.services.reminder_service import scheduler
    jobs = scheduler.get_jobs()
    await message.answer(f"Планировщик работает. Заданий в очереди: {len(jobs)}")


async def main():
    init_db()
    logger.info("Бот запускается...")

    # Планировщик уже инициализирован при импорте модуля

    # Подключаем роутеры
    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(broadcast.router)
    dp.include_router(superadmin.router)
    dp.include_router(library.router)
    dp.include_router(library_admin.router)
    dp.include_router(feedback.router)
    dp.include_router(feedback_admin.router)
    dp.include_router(chat.router)
    dp.include_router(chat_admin.router)
    dp.include_router(question.router)
    dp.include_router(question_admin.router)
    dp.include_router(reminders.router)
    dp.include_router(reminders_admin.router)

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
