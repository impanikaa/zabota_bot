from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from sqlalchemy import func

from app.db.session import Session
from app.db.models import Quote
from app.utils.roles import get_user_role

router = Router()


class QuoteStates(StatesGroup):
    waiting_text = State()
    waiting_category = State()


@router.message(F.text == "✏️ Управление цитатами")
async def manage_quotes(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа.")

    markup = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить цитату")],
            [KeyboardButton(text="📋 Список цитат")],
            [KeyboardButton(text="📊 Статистика цитат")],
            [KeyboardButton(text="⬅️ Назад в админку")]
        ],
        resize_keyboard=True
    )
    await message.answer("Управление мотивационными цитатами:", reply_markup=markup)


@router.message(F.text == "➕ Добавить цитату")
async def add_quote(message: Message, state: FSMContext):
    await message.answer("Введите текст цитаты:")
    await state.set_state(QuoteStates.waiting_text)


@router.message(QuoteStates.waiting_text)
async def add_quote_text(message: Message, state: FSMContext):
    if len(message.text) > 500:
        return await message.answer("Слишком длинная цитата. Максимум 500 символов.")

    await state.update_data(text=message.text)

    # Пропускаем выбор категории, сразу сохраняем цитату
    with Session() as session:
        quote = Quote(
            text=message.text,
            category="общие"  # Устанавливаем общую категорию по умолчанию
        )
        session.add(quote)
        session.commit()

    await message.answer("✅ Цитата добавлена!")
    await state.clear()


@router.message(F.text == "📋 Список цитат")
async def list_quotes(message: Message):
    with Session() as session:
        quotes = session.query(Quote).all()

        if not quotes:
            return await message.answer("Цитат пока нет.")

        text = "📋 Список цитат:\n\n"
        for i, quote in enumerate(quotes, 1):
            text += f"{i}. {quote.text[:50]}...\n"

        await message.answer(text)


@router.message(F.text == "📊 Статистика цитат")
async def quote_stats(message: Message):
    with Session() as session:
        total = session.query(Quote).count()
        await message.answer(f"📊 Всего цитат в базе: {total}")


@router.message(F.text == "⬅️ Назад в админку")
async def back_to_admin(message: Message, state: FSMContext):
    await state.clear()
    from app.handlers.admin import admin_panel
    await admin_panel(message)


# Добавляем обработчики команд
@router.message(F.text == "/list_quotes")
async def list_quotes_command(message: Message):
    await list_quotes(message)


@router.message(F.text == "/quote_stats")
async def quote_stats_command(message: Message):
    await quote_stats(message)