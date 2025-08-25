from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery

from app.db.session import Session
from app.db.models import User
from app.keyboards import get_main_menu
from app.utils.roles import get_user_role

router = Router()

class ProfileStates(StatesGroup):
    grade = State()
    subjects = State()
    region = State()
    username = State()
    consent = State()
    role = 0

@router.callback_query(F.data == "fill_profile")
async def handle_fill_profile(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_profile(callback.message, state)

@router.message(F.text == "📝 Заполнить/обновить")
async def cmd_profile(message: Message, state: FSMContext):
    await start_profile(message, state)

async def start_profile(message: Message, state: FSMContext):
    session = Session()
    user_id = message.from_user.id
    user = session.query(User).filter_by(user_id=user_id).first()
    if not user:
        user = User(user_id=user_id)
        session.add(user)
        session.commit()

    await message.answer("В каком ты классе в 25/26 учебном году? (введи число или '-', чтобы пропустить.)")
    await state.set_state(ProfileStates.grade)


@router.message(ProfileStates.grade)
async def set_grade(message: Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(grade=None)
    else:
        try:
            grade = int(message.text.strip())
            if grade not in range(1, 12):
                raise ValueError
            await state.update_data(grade=grade)
        except ValueError:
            return await message.answer("Пожалуйста, введи целое число от 1 до 11 или '-'.")

    await message.answer("Какими предметами ты в основном занимаешься? (через запятую или '-', чтобы пропустить)")
    await state.set_state(ProfileStates.subjects)


@router.message(ProfileStates.subjects)
async def set_subjects(message: Message, state: FSMContext):
    if message.text.strip() == "-":
        await state.update_data(subjects=None)
    else:
        await state.update_data(subjects=message.text.strip())

    await message.answer("Из какого ты региона/города? (или '-' чтобы пропустить)")
    await state.set_state(ProfileStates.region)

@router.message(ProfileStates.region)
async def set_region(message: Message, state: FSMContext):
    await state.update_data(region=message.text.strip())

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        f"Хочешь сохранить свой Telegram-ник @{message.from_user.username or 'неизвестно'} в анкете?",
        reply_markup=markup
    )
    await state.set_state(ProfileStates.username)

@router.message(ProfileStates.username)
async def set_username(message: Message, state: FSMContext):
    if message.text.strip() not in ["✅ Да", "❌ Нет"]:
        return await message.answer("Пожалуйста, выбери ✅ Да или ❌ Нет с клавиатуры.")

    if "✅" in message.text:
        await state.update_data(username=message.from_user.username or "")
    else:
        await state.update_data(username=None)

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True
    )
    await message.answer("Ты согласен(а) на обработку данных в рамках проекта?", reply_markup=markup)
    await state.set_state(ProfileStates.consent)

@router.message(ProfileStates.consent)
async def set_consent(message: Message, state: FSMContext):
    if message.text.strip() not in ["✅ Да", "❌ Нет"]:
        return await message.answer("Пожалуйста, выбери ✅ Да или ❌ Нет с клавиатуры.")

    consent = "✅" in message.text
    session = Session()
    user = session.query(User).filter_by(user_id=message.from_user.id).first()

    if not user:
        await message.answer("Что-то пошло не так. Попробуй ещё раз с /start или 📝 «Заполнить/обновить».")
        await state.clear()
        return

    if not consent:
        user.grade = None
        user.subjects = None
        user.region = None
        user.username = None
        user.consent = False
        session.commit()

        await message.answer(
            "Анкета удалена ❌, так как ты не дал(а) согласие на обработку данных.",
            reply_markup=get_main_menu(get_user_role(message.from_user.id))
        )
        await state.clear()
        return

    data = await state.get_data()
    user.grade = data["grade"]
    user.subjects = data["subjects"]
    user.region = data["region"]
    user.username = data.get("username")
    user.consent = True
    session.commit()

    role = get_user_role(message.from_user.id)
    await message.answer("Спасибо! Профиль обновлён ✅", reply_markup=get_main_menu(role))
    await state.clear()

@router.message(F.text == "👤 Профиль")
async def profile_menu(message: Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📄 Посмотреть анкету")],
            [KeyboardButton(text="📝 Заполнить/обновить")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Что хочешь сделать с профилем?", reply_markup=markup)


@router.message(F.text == "📄 Посмотреть анкету")
async def show_profile(message: Message):
    session = Session()
    user = session.query(User).filter_by(user_id=message.from_user.id).first()
    if not user:
        return await message.answer("Ты пока не заполнял анкету.")

    text = f"""📄 Твоя анкета:
🧑 Ник: @{user.username if user.username else "не указан"}
🎓 Класс: {user.grade or "не указан"}
📚 Предметы: {user.subjects or "не указаны"}
🌍 Регион: {user.region or "не указан"}
✅ Согласие: {"Да" if user.consent else "Нет"}
"""
    await message.answer(text)
