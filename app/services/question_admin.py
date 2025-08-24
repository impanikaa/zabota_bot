from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import Session
from app.db.models import Feedback, User
from app.utils.roles import get_user_role
from app.config import ADMIN_IDS as ADMINS

router = Router()


class AnswerQuestionStates(StatesGroup):
    waiting_answer = State()


class HideQuestionStates(StatesGroup):
    waiting_question_id = State()


@router.message(F.text == "❓ Вопросы админу")
async def question_panel(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа к вопросам.")

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 Неотвеченные", callback_data="question_unanswered")],
            [InlineKeyboardButton(text="📖 Все вопросы", callback_data="question_all")],
            [InlineKeyboardButton(text="👁️ Скрытые вопросы", callback_data="question_hidden")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="question_back")]
        ]
    )
    await message.answer("❓ Панель вопросов администрации:", reply_markup=markup)


@router.callback_query(F.data == "question_unanswered")
async def show_unanswered_questions(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id

    questions = session.query(Feedback).filter(
        Feedback.request_type == 'question',
        Feedback.is_hidden == False,
        ~Feedback.read_by.contains(str(admin_id))
    ).all()

    if not questions:
        return await call.message.edit_text("✅ Все вопросы отвечены!")

    text = "📩 <b>Неотвеченные вопросы:</b>\n\n"
    for q in questions:
        date_str = q.created_at.strftime("%d.%m.%Y %H:%M")
        text += f"🆔 <b>ID {q.id}</b> | 📅 {date_str}\n{q.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "question_all")
async def show_all_questions(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id
    questions = session.query(Feedback).filter(
        Feedback.request_type == 'question',
        Feedback.is_hidden == False
    ).all()

    if not questions:
        return await call.message.edit_text("❌ Вопросов пока нет.")

    text = "📖 <b>Все вопросы администрации:</b>\n\n"
    for q in questions:
        date_str = q.created_at.strftime("%d.%m.%Y %H:%M")

        read_by_list = q.read_by.split(",") if q.read_by else []
        if str(admin_id) in read_by_list:
            status_icon = "✅"
        else:
            status_icon = "📩"

        read_count = len(read_by_list)
        total_admins = len(ADMINS)
        status_text = f"{status_icon} ({read_count}/{total_admins})"

        text += f"{status_text} | 🆔 <b>ID {q.id}</b> | 📅 {date_str}\n{q.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "question_hidden")
async def show_hidden_questions(call: CallbackQuery):
    session = Session()
    questions = session.query(Feedback).filter(
        Feedback.request_type == 'question',
        Feedback.is_hidden == True
    ).all()

    if not questions:
        return await call.message.edit_text("❌ Скрытых вопросов нет.")

    text = "👁️ <b>Скрытые вопросы:</b>\n\n"
    for q in questions:
        date_str = q.created_at.strftime("%d.%m.%Y %H:%M")

        read_count = len(q.read_by.split(",")) if q.read_by else 0
        status = "✅" if read_count > 0 else "📩"

        text += f"{status} 🆔 <b>ID {q.id}</b> | 📅 {date_str}\n{q.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "question_back")
async def back_from_question(call: CallbackQuery):
    await call.message.edit_text("⬅️ Возврат в админку.")


@router.callback_query(F.data.startswith("answer_question_"))
async def answer_question_callback(call: CallbackQuery, state: FSMContext):
    question_id = int(call.data.split("_")[-1])

    session = Session()
    question = session.query(Feedback).get(question_id)

    if not question:
        await call.answer("Вопрос не найден")
        return

    if question.request_type != 'question':
        await call.answer("Это не вопрос администрации")
        return

    # Помечаем вопрос как прочитанный
    read_by = question.read_by.split(",") if question.read_by else []
    if str(call.from_user.id) not in read_by:
        read_by.append(str(call.from_user.id))
        question.read_by = ",".join(read_by)
        session.commit()

    await state.update_data(question_id=question_id, user_id=question.user_id)
    await call.message.answer("Введи ответ на вопрос:")
    await state.set_state(AnswerQuestionStates.waiting_answer)

    await call.answer()


@router.message(AnswerQuestionStates.waiting_answer)
async def process_answer(message: Message, state: FSMContext):
    answer_text = message.text.strip()
    data = await state.get_data()
    question_id = data.get("question_id")
    user_id = data.get("user_id")

    # Отправляем ответ пользователю
    try:
        await message.bot.send_message(
            chat_id=user_id,
            text=f"📩 Ответ от администрации на ваш вопрос:\n\n{answer_text}"
        )
        await message.answer(f"✅ Ответ отправлен пользователю!")
    except Exception as e:
        await message.answer("❌ Не удалось отправить ответ пользователю. Возможно, он заблокировал бота.")

    await state.clear()


@router.message(F.text == "📝 Ответить на вопрос")
async def answer_question_button(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав.")

    await message.answer("Введи ID вопроса, на который хочешь ответить:")
    await state.set_state(HideQuestionStates.waiting_question_id)


@router.message(HideQuestionStates.waiting_question_id)
async def process_question_id(message: Message, state: FSMContext):
    try:
        question_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    session = Session()
    question = session.query(Feedback).get(question_id)

    if not question:
        await message.answer("❌ Вопрос с таким ID не найден.")
        await state.clear()
        return

    if question.request_type != 'question':
        await message.answer("❌ Это не вопрос администрации.")
        await state.clear()
        return

    # Помечаем вопрос как прочитанный
    read_by = question.read_by.split(",") if question.read_by else []
    if str(message.from_user.id) not in read_by:
        read_by.append(str(message.from_user.id))
        question.read_by = ",".join(read_by)
        session.commit()

    await state.update_data(question_id=question_id, user_id=question.user_id)
    await message.answer("Введи ответ на вопрос:")
    await state.set_state(AnswerQuestionStates.waiting_answer)


@router.message(F.text.startswith("/hide_question"))
async def hide_question_command(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав для этой команды.")

    try:
        question_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /hide_question <ID>")
        return

    session = Session()
    question = session.query(Feedback).get(question_id)

    if not question:
        await message.answer("❌ Вопрос с таким ID не найден.")
        return

    if question.request_type != 'question':
        await message.answer("❌ Это не вопрос администрации, нельзя скрыть.")
        return

    question.is_hidden = True
    session.commit()

    await message.answer(f"✅ Вопрос ID {question_id} скрыт!")


@router.message(HideQuestionStates.waiting_question_id)
async def process_hide_question(message: Message, state: FSMContext):
    try:
        question_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    session = Session()
    question = session.query(Feedback).get(question_id)

    if not question:
        await message.answer("❌ Вопрос с таким ID не найден.")
        await state.clear()
        return

    if question.request_type != 'question':
        await message.answer("❌ Это не вопрос администрации, нельзя скрыть.")
        await state.clear()
        return

    question.is_hidden = True
    session.commit()

    await message.answer(f"✅ Вопрос ID {question_id} скрыт!")
    await state.clear()