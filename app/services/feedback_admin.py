from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import Session
from aiogram.fsm.state import State, StatesGroup
from app.db.models import Feedback, User
from app.utils.roles import get_user_role
from app.config import ADMIN_IDS as ADMINS

router = Router()

class MarkReadStates(StatesGroup):
    waiting_feedback_id = State()

# 📋 Панель отзывов
@router.message(F.text == "💌 Отзывы")
async def feedback_panel(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа к отзывам.")

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Непрочитанные", callback_data="feedback_unread")],
            [InlineKeyboardButton(text="📖 Все отзывы", callback_data="feedback_all")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="feedback_back")]
        ]
    )
    await message.answer("💌 Панель отзывов:", reply_markup=markup)


# 🔎 Показать непрочитанные отзывы
@router.callback_query(F.data == "feedback_unread")
async def show_unread_feedbacks(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id

    feedbacks = session.query(Feedback).filter(
        ~Feedback.read_by.contains(str(admin_id))
    ).all()

    if not feedbacks:
        return await call.message.edit_text("✅ Все отзывы прочитаны!")

    text = "📩 <b>Непрочитанные отзывы:</b>\n\n"
    for fb in feedbacks:
        # Форматируем дату
        date_str = fb.created_at.strftime("%d.%m.%Y %H:%M")

        user_info = ""
        if fb.include_profile:
            user = session.query(User).filter_by(user_id=fb.user_id).first()
            if user:
                user_info = f"\n👤 {user.username or '-'}, {user.region or '-'}, {user.grade or '-'} класс"

        text += f"🆔 <b>ID {fb.id}</b> | 📅 {date_str}\n{fb.text}{user_info}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


# 📖 Показать все отзывы
@router.callback_query(F.data == "feedback_all")
async def show_all_feedbacks(call: CallbackQuery):
    session = Session()
    feedbacks = session.query(Feedback).all()

    if not feedbacks:
        return await call.message.edit_text("❌ Отзывов пока нет.")

    text = "📖 <b>Все отзывы:</b>\n\n"
    for fb in feedbacks:
        # Форматируем дату
        date_str = fb.created_at.strftime("%d.%m.%Y %H:%M")

        # Статус прочтения
        read_count = len(fb.read_by.split(",")) if fb.read_by else 0
        total_admins = len(ADMINS)
        status_icon = "✅" if read_count == total_admins else "📩"
        status_text = f"{status_icon} ({read_count}/{total_admins})"

        user_info = ""
        if fb.include_profile:
            user = session.query(User).filter_by(user_id=fb.user_id).first()
            if user:
                user_info = f"\n👤 {user.username or '-'}, {user.region or '-'}, {user.grade or '-'} класс"

        text += f"{status_text} | 🆔 <b>ID {fb.id}</b> | 📅 {date_str}\n{fb.text}{user_info}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


# 🔙 Назад
@router.callback_query(F.data == "feedback_back")
async def back_from_feedback(call: CallbackQuery):
    await call.message.edit_text("⬅️ Возврат в админку.")


# Команда для отметки отзыва прочитанным
@router.message(F.text == "/mark_read")
async def start_mark_read(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав для этой команды.")

    await message.answer("Введи ID отзыва, который хочешь отметить как прочитанный:")
    await state.set_state(MarkReadStates.waiting_feedback_id)


@router.message(MarkReadStates.waiting_feedback_id)
async def process_mark_read(message: Message, state: FSMContext):
    try:
        feedback_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    admin_id = message.from_user.id
    session = Session()
    fb = session.query(Feedback).get(feedback_id)

    if not fb:
        await message.answer("❌ Отзыв с таким ID не найден.")
        await state.clear()
        return

    read_by = fb.read_by.split(",") if fb.read_by else []
    if str(admin_id) not in read_by:
        read_by.append(str(admin_id))
        fb.read_by = ",".join(read_by)
        session.commit()

        read_count = len(read_by)
        total_admins = len(ADMINS)

        await message.answer(
            f"✅ Отзыв ID {feedback_id} отмечен как прочитанный!\n"
            f"Статус: {read_count}/{total_admins} админов прочитали"
        )
    else:
        await message.answer("ℹ️ Ты уже отмечал этот отзыв как прочитанный.")

    await state.clear()


@router.message(F.text == "📝 Отметить прочитанным")
async def mark_read_button(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав.")

    await message.answer("Введи ID отзыва, который хочешь отметить как прочитанный:")
    await state.set_state(MarkReadStates.waiting_feedback_id)