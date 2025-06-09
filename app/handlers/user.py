from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

from app.db.session import Session
from app.db.models import User
from app.main import get_main_menu

router = Router()

class ProfileStates(StatesGroup):
    grade = State()
    subjects = State()
    region = State()
    username = State()
    consent = State()

@router.message(F.text == "📝 Заполнить/обновить")
async def cmd_profile(message: Message, state: FSMContext):
    await message.answer("Какой у тебя класс? (от 1 до 11)")
    await state.set_state(ProfileStates.grade)

@router.message(ProfileStates.grade)
async def set_grade(message: Message, state: FSMContext):
    try:
        grade = int(message.text.strip())
        if grade not in range(1, 12):
            raise ValueError
    except ValueError:
        return await message.answer("Пожалуйста, введи целое число от 1 до 11.")
    await state.update_data(grade=grade)
    await message.answer("Какие предметы ты пишешь на олимпиадах, сдаёшь или любишь? (через запятую)")
    await state.set_state(ProfileStates.subjects)

@router.message(ProfileStates.subjects)
async def set_subjects(message: Message, state: FSMContext):
    await state.update_data(subjects=message.text.strip())
    await message.answer("Из какого ты региона/города?")
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
        await message.answer("Что-то пошло не так. Попробуй снова /start.")
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
            reply_markup=get_main_menu()
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

    await message.answer("Спасибо! Профиль обновлён ✅", reply_markup=get_main_menu())
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
