from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from app.db.session import Session
from app.db.models import Feedback, User
from app.config import ADMIN_IDS as ADMINS
from app.keyboards import get_support_menu
from app.utils.format import format_user_info

router = Router()

class ChatStates(StatesGroup):
    waiting_problem = State()
    waiting_permissions = State()

@router.message(F.text == "🙏 #болталка")
async def start_chat(message: Message, state: FSMContext):
    await message.answer(
        "💬 Расскажи о своей проблеме или ситуации, которой хочешь поделиться.",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(ChatStates.waiting_problem)

@router.message(ChatStates.waiting_problem)
async def process_problem(message: Message, state: FSMContext):
    await state.update_data(problem_text=message.text)

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Всё разрешаю", callback_data="permission_yes_yes"),
            InlineKeyboardButton(text="📝 Только опубликовать", callback_data="permission_yes_no")
        ],
        [
            InlineKeyboardButton(text="👤 Только профиль", callback_data="permission_no_yes"),
            InlineKeyboardButton(text="❌ Ничего не разрешаю", callback_data="permission_no_no")
        ]
    ])

    await message.answer(
        "Что разрешаешь?\n\n"
        "• ✅ Всё - опубликовать и использовать профиль\n"
        "• 📝 Только опубликовать (без профиля)\n"
        "• 👤 Только использовать профиль (не публиковать)\n"
        "• ❌ Ничего не разрешаю",
        reply_markup=markup
    )
    await state.set_state(ChatStates.waiting_permissions)

@router.callback_query(ChatStates.waiting_permissions, F.data.startswith("permission_"))
async def process_permissions(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    problem_text = data.get("problem_text", "")

    if not problem_text:
        await call.message.answer("❌ Произошла ошибка. Попробуйте начать заново.")
        await state.clear()
        return

    _, publish_perm, profile_perm = call.data.split("_")
    can_publish = (publish_perm == "yes")
    include_profile = (profile_perm == "yes")

    session = Session()
    fb = Feedback(
        user_id=call.from_user.id,
        text=problem_text,
        include_profile=include_profile,
        request_type='chat',
        can_publish=can_publish,
        is_published=False
    )
    session.add(fb)
    session.commit()

    response_text = "💛 Спасибо! Твой вопрос сохранён."
    if not can_publish:
        response_text += " Он не будет опубликован."
    if include_profile:
        response_text += " Данные из анкеты добавлены."

    await call.message.answer(response_text, reply_markup=get_support_menu())

    user = session.query(User).filter_by(user_id=call.from_user.id).first()
    user_info = format_user_info(user, include_profile)

    for admin_id in ADMINS:
        if can_publish:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Опубликовано", callback_data=f"mark_published_{fb.id}")]]
            )
        else:
            markup = None

        await call.bot.send_message(
            chat_id=admin_id,
            text=f"💬 Новый запрос в #болталку:\n\n{fb.text}\n{f'👤 {user_info}' if user_info else ''}",
            reply_markup=markup
        )

    await state.clear()