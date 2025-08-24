from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import Session
from aiogram.fsm.state import State, StatesGroup
from app.db.models import Feedback, User
from app.utils.roles import get_user_role
from app.config import ADMIN_IDS as ADMINS
from app.utils.format import format_user_info

router = Router()


class MarkReadStates(StatesGroup):
    waiting_feedback_id = State()


class HideFeedbackStates(StatesGroup):
    waiting_feedback_id = State()


@router.message(F.text == "💌 Отзывы")
async def feedback_panel(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа к отзывам.")

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Непрочитанные", callback_data="feedback_unread")],
            [InlineKeyboardButton(text="📖 Все отзывы", callback_data="feedback_all")],
            [InlineKeyboardButton(text="👁️ Скрытые отзывы", callback_data="feedback_hidden")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="feedback_back")]
        ]
    )
    await message.answer("💌 Панель отзывов:", reply_markup=markup)


@router.callback_query(F.data == "feedback_unread")
async def show_unread_feedbacks(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id

    feedbacks = session.query(Feedback).filter(
        Feedback.request_type == 'feedback',
        Feedback.is_hidden == False,
        ~Feedback.read_by.contains(str(admin_id))
    ).all()

    if not feedbacks:
        return await call.message.edit_text("✅ Все отзывы прочитаны!")

    text = "📩 <b>Непрочитанные отзывы:</b>\n\n"
    for fb in feedbacks:
        date_str = fb.created_at.strftime("%d.%m.%Y %H:%M")
        user = session.query(User).filter_by(user_id=fb.user_id).first()
        user_info = format_user_info(user, fb.include_profile)

        text += f"🆔 <b>ID {fb.id}</b> | 📅 {date_str}{f' | 👤 {user_info}' if user_info else ''}\n{fb.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "feedback_all")
async def show_all_feedbacks(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id
    feedbacks = session.query(Feedback).filter(
        Feedback.request_type == 'feedback',
        Feedback.is_hidden == False
    ).all()

    if not feedbacks:
        return await call.message.edit_text("❌ Отзывов пока нет.")

    text = "📖 <b>Все отзывы:</b>\n\n"
    for fb in feedbacks:
        date_str = fb.created_at.strftime("%d.%m.%Y %H:%M")

        read_by_list = fb.read_by.split(",") if fb.read_by else []
        if str(admin_id) in read_by_list:
            status_icon = "✅"
        else:
            status_icon = "📩"

        read_count = len(read_by_list)
        total_admins = len(ADMINS)
        status_text = f"{status_icon} ({read_count}/{total_admins})"

        user = session.query(User).filter_by(user_id=fb.user_id).first()
        user_info = format_user_info(user, fb.include_profile)

        text += f"{status_text} | 🆔 <b>ID {fb.id}</b> | 📅 {date_str}{f' | 👤 {user_info}' if user_info else ''}\n{fb.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "feedback_hidden")
async def show_hidden_feedbacks(call: CallbackQuery):
    session = Session()
    feedbacks = session.query(Feedback).filter(
        Feedback.request_type == 'feedback',
        Feedback.is_hidden == True
    ).all()

    if not feedbacks:
        return await call.message.edit_text("❌ Скрытых отзывов нет.")

    text = "👁️ <b>Скрытые отзывы:</b>\n\n"
    for fb in feedbacks:
        date_str = fb.created_at.strftime("%d.%m.%Y %H:%M")

        # Определяем статус отзыва
        read_count = len(fb.read_by.split(",")) if fb.read_by else 0
        status = "✅" if read_count > 0 else "📩"

        user = session.query(User).filter_by(user_id=fb.user_id).first()

        if fb.include_profile and user and user.consent:
            user_info = format_user_info(user, fb.include_profile)
            user_display = f"👤 {user_info}" if user_info else ""
        else:
            user_display = ""

        text += f"{status} 🆔 <b>ID {fb.id}</b> | 📅 {date_str}{f' | {user_display}' if user_display else ''}\n{fb.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "feedback_back")
async def back_from_feedback(call: CallbackQuery):
    await call.message.edit_text("⬅️ Возврат в админку.")


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

    if fb.request_type != 'feedback':
        await message.answer("❌ Это не отзыв, нельзя отметить как прочитанный.")
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


@router.message(F.text.startswith("/hide_feedback"))
async def hide_feedback_command(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав для этой команды.")

    try:
        feedback_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /hide_feedback <ID>")
        return

    session = Session()
    fb = session.query(Feedback).get(feedback_id)

    if not fb:
        await message.answer("❌ Отзыв с таким ID не найден.")
        return

    if fb.request_type != 'feedback':
        await message.answer("❌ Это не отзыв, нельзя скрыть.")
        return

    fb.is_hidden = True
    session.commit()

    await message.answer(f"✅ Отзыв ID {feedback_id} скрыт!")


@router.message(HideFeedbackStates.waiting_feedback_id)
async def process_hide_feedback(message: Message, state: FSMContext):
    try:
        feedback_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    session = Session()
    fb = session.query(Feedback).get(feedback_id)

    if not fb:
        await message.answer("❌ Отзыв с таким ID не найден.")
        await state.clear()
        return

    if fb.request_type != 'feedback':
        await message.answer("❌ Это не отзыв, нельзя скрыть.")
        await state.clear()
        return

    fb.is_hidden = True
    session.commit()

    await message.answer(f"✅ Отзыв ID {feedback_id} скрыт!")
    await state.clear()