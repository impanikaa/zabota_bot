from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton, ReplyKeyboardRemove
from datetime import datetime, time
import json
import random

from app.db.session import Session
from app.db.models import UserReminder, Quote, ReminderStat
from app.keyboards import get_main_menu
from app.utils.roles import get_user_role

router = Router()


class ReminderStates(StatesGroup):
    choosing_type = State()
    choosing_habit = State()
    custom_habit = State()
    setting_schedule = State()
    setting_fixed_times = State()
    setting_interval = State()
    setting_random_interval = State()
    setting_quiet_time = State()
    editing_reminder = State()
    deleting_reminder = State()


# Предустановленные привычки
PREDEFINED_HABITS = {
    "water": "💧 Выпить стакан воды",
    "posture": "🧘 Проверить осанку",
    "eyes": "👀 Сделать зарядку для глаз",
    "stretch": "🔁 Размяться и потянуться"
}


@router.message(F.text == "⏰ Напоминания")
async def reminders_main(message: Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить напоминание")],
            [KeyboardButton(text="📋 Мои напоминания")],
            [KeyboardButton(text="🗑️ Удалить напоминания")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Управление напоминаниями:", reply_markup=markup)


@router.message(F.text == "➕ Добавить напоминание")
async def add_reminder(message: Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏃 Привычка"), KeyboardButton(text="💬 Цитата")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери тип напоминания:", reply_markup=markup)
    await state.set_state(ReminderStates.choosing_type)


@router.message(ReminderStates.choosing_type, F.text.in_(["🏃 Привычка", "💬 Цитата"]))
async def process_type(message: Message, state: FSMContext):
    reminder_type = "habit" if message.text == "🏃 Привычка" else "quote"
    await state.update_data(type=reminder_type)

    if reminder_type == "habit":
        markup = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💧 Вода"), KeyboardButton(text="🧘 Осанка")],
                [KeyboardButton(text="👀 Глаза"), KeyboardButton(text="🔁 Разминка")],
                [KeyboardButton(text="✏️ Своя привычка"), KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выбери привычку:", reply_markup=markup)
        await state.set_state(ReminderStates.choosing_habit)
    else:
        await set_schedule_type(message, state)


@router.message(ReminderStates.choosing_habit, F.text.in_(["💧 Вода", "🧘 Осанка", "👀 Глаза", "🔁 Разминка"]))
async def process_predefined_habit(message: Message, state: FSMContext):
    habit_map = {
        "💧 Вода": "water",
        "🧘 Осанка": "posture",
        "👀 Глаза": "eyes",
        "🔁 Разминка": "stretch"
    }
    habit_type = habit_map[message.text]
    await state.update_data(habit_type=habit_type)
    await set_schedule_type(message, state)


@router.message(ReminderStates.choosing_habit, F.text == "✏️ Своя привычка")
async def custom_habit(message: Message, state: FSMContext):
    await message.answer("Напиши свою привычку текстом:")
    await state.set_state(ReminderStates.custom_habit)


@router.message(ReminderStates.custom_habit)
async def process_custom_habit(message: Message, state: FSMContext):
    if len(message.text) > 100:
        return await message.answer("Слишком длинный текст. Максимум 100 символов.")

    await state.update_data(custom_text=message.text)
    await set_schedule_type(message, state)


async def set_schedule_type(message: Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🕐 В определённое время"), KeyboardButton(text="🔄 С интервалом")],
            [KeyboardButton(text="🎲 Случайное время"), KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери тип расписания:", reply_markup=markup)
    await state.set_state(ReminderStates.setting_schedule)


@router.message(ReminderStates.setting_schedule,
                F.text.in_(["🕐 В определённое время", "🔄 С интервалом", "🎲 Случайное время"]))
async def process_schedule_type(message: Message, state: FSMContext):
    if message.text == "🕐 В определённое время":
        schedule_type = "fixed"
        await state.update_data(schedule_type=schedule_type)
        await message.answer("Введи время отправки через запятую (например: 09:00, 13:00, 18:00)")
        await state.set_state(ReminderStates.setting_fixed_times)
    elif message.text == "🔄 С интервалом":
        schedule_type = "interval"
        await state.update_data(schedule_type=schedule_type)
        await message.answer("Введи интервал в часах (например: 3 для напоминания каждые 3 часа)")
        await state.set_state(ReminderStates.setting_interval)
    else:
        schedule_type = "random"
        await state.update_data(schedule_type=schedule_type)
        await message.answer(
            "Введи интервал в часах для случайного напоминания (например: 6 для напоминания раз в 6 часов в случайный момент)")
        await state.set_state(ReminderStates.setting_random_interval)


@router.message(ReminderStates.setting_fixed_times)
async def process_fixed_times(message: Message, state: FSMContext):
    times = [t.strip() for t in message.text.split(",")]
    valid_times = []

    for t in times:
        try:
            datetime.strptime(t, "%H:%M")
            valid_times.append(t)
        except ValueError:
            await message.answer(f"Неверный формат времени: {t}. Используй формат ЧЧ:ММ")
            return

    await state.update_data(times=json.dumps(valid_times))
    await set_quiet_time(message, state)


@router.message(ReminderStates.setting_interval)
async def process_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text)
        if interval < 1:
            raise ValueError
        await state.update_data(interval_hours=interval)
        await set_quiet_time(message, state)
    except ValueError:
        await message.answer("Введи положительное число")


@router.message(ReminderStates.setting_random_interval)
async def process_random_interval(message: Message, state: FSMContext):
    try:
        interval = int(message.text)
        if interval < 1:
            raise ValueError
        await state.update_data(random_interval_hours=interval)
        await set_quiet_time(message, state)
    except ValueError:
        await message.answer("Введи положительное число")


async def set_quiet_time(message: Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Оставить по умолчанию (23:00-06:00)")],
            [KeyboardButton(text="✏️ Настроить своё время")],
            [KeyboardButton(text="❌ Без тихого времени")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
    await message.answer("Настроить тихое время (когда не беспокоить)?", reply_markup=markup)
    await state.set_state(ReminderStates.setting_quiet_time)


@router.message(ReminderStates.setting_quiet_time, F.text == "✅ Оставить по умолчанию (23:00-06:00)")
async def process_default_quiet_time(message: Message, state: FSMContext):
    await save_reminder(message, state, "23:00", "06:00")


@router.message(ReminderStates.setting_quiet_time, F.text == "✏️ Настроить своё время")
async def custom_quiet_time(message: Message, state: FSMContext):
    await message.answer("Введи тихое время в формате 'начало-конец' (например: 23:00-07:00)")


@router.message(ReminderStates.setting_quiet_time, F.text == "❌ Без тихого времени")
async def no_quiet_time(message: Message, state: FSMContext):
    await save_reminder(message, state, None, None)


@router.message(ReminderStates.setting_quiet_time)
async def process_custom_quiet_time(message: Message, state: FSMContext):
    if "-" not in message.text:
        return await message.answer("Используй формат 'начало-конец' (например: 23:00-07:00)")

    try:
        start, end = message.text.split("-", 1)
        datetime.strptime(start.strip(), "%H:%M")
        datetime.strptime(end.strip(), "%H:%M")
        await save_reminder(message, state, start.strip(), end.strip())
    except ValueError:
        await message.answer("Неверный формат времени. Используй ЧЧ:ММ")


async def save_reminder(message: Message, state: FSMContext, quiet_start: str, quiet_end: str):
    data = await state.get_data()

    with Session() as session:
        reminder = UserReminder(
            user_id=message.from_user.id,
            type=data['type'],
            habit_type=data.get('habit_type'),
            custom_text=data.get('custom_text'),
            schedule_type=data['schedule_type'],
            times=data.get('times'),
            interval_hours=data.get('interval_hours'),
            random_interval_hours=data.get('random_interval_hours'),
            start_time=quiet_start,
            end_time=quiet_end
        )
        session.add(reminder)
        session.commit()

        # Немедленно планируем напоминание
        from app.services.reminder_service import schedule_reminder
        schedule_reminder(reminder)

    await message.answer("✅ Напоминание добавлено!", reply_markup=get_main_menu(get_user_role(message.from_user.id)))
    await state.clear()


@router.message(F.text == "📋 Мои напоминания")
async def list_reminders(message: Message):
    with Session() as session:
        reminders = session.query(UserReminder).filter_by(
            user_id=message.from_user.id,
            is_active=True
        ).all()

        if not reminders:
            return await message.answer("У тебя пока нет активных напоминаний")

        text = "📋 Твои напоминания:\n\n"
        for i, rem in enumerate(reminders, 1):
            if rem.type == 'habit':
                if rem.habit_type:
                    habit_text = PREDEFINED_HABITS[rem.habit_type]
                else:
                    habit_text = rem.custom_text
                text += f"{i}. 🏃 {habit_text}\n"
            else:
                text += f"{i}. 💬 Мотивационная цитата\n"

            if rem.schedule_type == 'fixed':
                times = json.loads(rem.times)
                text += f"   🕐 Время: {', '.join(times)}\n"
            elif rem.schedule_type == 'interval':
                text += f"   🔄 Каждые {rem.interval_hours} ч.\n"
            else:
                text += f"   🎲 Случайно каждые {rem.random_interval_hours} ч.\n"

            if rem.start_time and rem.end_time:
                text += f"   🤫 Тихие часы: {rem.start_time}-{rem.end_time}\n\n"
            else:
                text += f"   🤫 Тихие часы: нет\n\n"

        await message.answer(text)


@router.message(F.text == "🗑️ Удалить напоминания")
async def delete_reminders(message: Message, state: FSMContext):
    with Session() as session:
        reminders = session.query(UserReminder).filter_by(
            user_id=message.from_user.id,
            is_active=True
        ).all()

        if not reminders:
            return await message.answer("У тебя пока нет активных напоминаний")

        text = "🗑️ Выбери номер напоминания для удаления:\n\n"
        for i, rem in enumerate(reminders, 1):
            if rem.type == 'habit':
                if rem.habit_type:
                    habit_text = PREDEFINED_HABITS[rem.habit_type]
                else:
                    habit_text = rem.custom_text
                text += f"{i}. 🏃 {habit_text}\n"
            else:
                text += f"{i}. 💬 Мотивационная цитата\n"

        await message.answer(text)
        await state.set_state(ReminderStates.deleting_reminder)
        await state.update_data(reminders=[r.id for r in reminders])


@router.message(ReminderStates.deleting_reminder)
async def process_delete_reminder(message: Message, state: FSMContext):
    try:
        number = int(message.text.strip())
        data = await state.get_data()
        reminders = data.get('reminders', [])

        if number < 1 or number > len(reminders):
            await message.answer("Неверный номер. Попробуй еще раз.")
            return

        reminder_id = reminders[number - 1]

        with Session() as session:
            reminder = session.query(UserReminder).get(reminder_id)
            if reminder and reminder.user_id == message.from_user.id:
                # Удаляем из планировщика
                from app.services.reminder_service import remove_reminder
                remove_reminder(reminder_id)

                session.delete(reminder)
                session.commit()
                await message.answer("✅ Напоминание удалено!")
            else:
                await message.answer("Не удалось найти напоминание.")

        await state.clear()
    except ValueError:
        await message.answer("Введи номер цифрами.")


@router.message(F.text == "⬅️ Назад")
async def back_from_reminders(message: Message, state: FSMContext):
    await state.clear()
    role = get_user_role(message.from_user.id)
    await message.answer("Главное меню:", reply_markup=get_main_menu(role))


@router.message(F.text == "/test_reminder")
async def test_reminder(message: Message):
    """Тестовая команда для проверки работы напоминаний"""
    try:
        from app.services.reminder_service import send_reminder

        # Создаем тестовое напоминание
        with Session() as session:
            reminder = UserReminder(
                user_id=message.from_user.id,
                type='habit',
                habit_type='water',
                schedule_type='fixed',
                times=json.dumps(["00:01"]),
                start_time=None,
                end_time=None
            )
            session.add(reminder)
            session.commit()

            # Немедленно отправляем напоминание
            await send_reminder(reminder.id)

        await message.answer("Тестовое напоминание отправлено!")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")


@router.message(F.text == "/reload_reminders")
async def reload_reminders(message: Message):
    """Перезагружает все напоминания в планировщике"""
    try:
        from app.services.reminder_service import load_reminders
        load_reminders()
        await message.answer("✅ Напоминания перезагружены!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при перезагрузке: {e}")