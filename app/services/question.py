from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from app.db.session import Session
from app.db.models import Feedback
from app.config import ADMIN_IDS as ADMINS
from app.keyboards import get_support_menu

router = Router()

class QuestionStates(StatesGroup):
    waiting_question = State()

@router.message(F.text == "❓ Вопрос администрации")
async def start_question(message: Message, state: FSMContext):
    await message.answer(
        "💬 Задай свой вопрос администрации проекта:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(QuestionStates.waiting_question)

@router.message(QuestionStates.waiting_question)
async def process_question(message: Message, state: FSMContext):
    session = Session()
    fb = Feedback(
        user_id=message.from_user.id,
        text=message.text,
        include_profile=False,  # Не используем данные профиля
        request_type='question',
        can_publish=False,  # Не для публикации
        is_published=False
    )
    session.add(fb)
    session.commit()

    await message.answer(
        "💛 Спасибо! Твой вопрос отправлен администрации. Ответим в ближайшее время.",
        reply_markup=get_support_menu()
    )

    # Уведомляем админов
    for admin_id in ADMINS:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📝 Ответить", callback_data=f"answer_question_{fb.id}")]]
        )

        await message.bot.send_message(
            chat_id=admin_id,
            text=f"❓ Новый вопрос администрации:\n\n{fb.text}",
            reply_markup=markup
        )

    await state.clear()