from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.db.session import Session
from app.utils.format import format_user_info
from app.db.models import Feedback, User
from app.config import ADMIN_IDS as ADMINS

router = Router()

class FeedbackForm(StatesGroup):
    waiting_text = State()
    waiting_profile_permission = State()

@router.message(F.text == "📝 Отзыв")
async def start_feedback(message: Message, state: FSMContext):
    await message.answer("✍️ Напиши свой отзыв или пожелания:")
    await state.set_state(FeedbackForm.waiting_text)

@router.message(FeedbackForm.waiting_text)
async def feedback_text(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="profile_yes")],
            [InlineKeyboardButton(text="Нет", callback_data="profile_no")]
        ]
    )
    await message.answer("Добавить данные из анкеты (регион, класс и т.п.)?", reply_markup=markup)
    await state.set_state(FeedbackForm.waiting_profile_permission)

@router.callback_query(F.data.in_(["profile_yes", "profile_no"]))
async def feedback_save(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "text" not in data:
        await call.message.answer("❌ Произошла ошибка. Попробуйте начать заново.")
        await state.clear()
        return

    include_profile = (call.data == "profile_yes")

    with Session() as session:
        fb = Feedback(
            user_id=call.from_user.id,
            text=data["text"],
            include_profile=include_profile
        )
        session.add(fb)
        session.commit()

        await call.message.answer("Спасибо за отзыв 💛")
        await state.clear()

        user = session.query(User).filter_by(user_id=call.from_user.id).first()
        user_info = format_user_info(user, include_profile)

        for admin_id in ADMINS:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="✅ Прочитано", callback_data=f"mark_read_{fb.id}")]]
            )

            await call.bot.send_message(
                chat_id=admin_id,
                text=f"📩 Новый отзыв:\n\n{fb.text}\n{f'👤 {user_info}' if user_info else ''}",
                reply_markup=markup
            )

@router.callback_query(F.data.startswith("mark_read_"))
async def mark_feedback_as_read(call: CallbackQuery):
    feedback_id = int(call.data.split("_")[-1])
    admin_id = call.from_user.id

    session = Session()
    fb = session.query(Feedback).get(feedback_id)

    if fb:
        read_by = fb.read_by.split(",") if fb.read_by else []
        if str(admin_id) not in read_by:
            read_by.append(str(admin_id))
            fb.read_by = ",".join(read_by)
            session.commit()

        read_count = len(read_by)
        total_admins = len(ADMINS)

        new_text = call.message.text + f"\n\n✅ Прочитано ({read_count}/{total_admins})"
        await call.message.edit_text(
            text=new_text,
            reply_markup=None
        )
    else:
        await call.answer("Отзыв не найден")