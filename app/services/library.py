# app/handlers/library.py
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db.session import Session
from app.db.models import Article

router = Router()

class LibraryStates(StatesGroup):
    reading = State()

def get_ordered_articles(session):
    return session.query(Article).order_by(Article.date.asc(), Article.id.asc()).all()

def list_articles_text(session) -> str:
    articles = get_ordered_articles(session)
    if not articles:
        return "📚 Библиотека пока пуста."
    text = "📚 Список статей:\n\n"
    for idx, a in enumerate(articles, start=1):
        text += f"{idx}. {a.title}\n"
    text += "\nНапиши номер статьи, чтобы открыть её (например: 1).\nКнопка «⬅️ Назад» вернёт в меню."
    return text

@router.message(F.text == "📚 Библиотека")
async def open_library(message: Message, state: FSMContext):
    session = Session()
    await state.set_state(LibraryStates.reading)

    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад")]],
        resize_keyboard=True
    )

    await message.answer(
        "📖 Здесь собраны статьи проекта «Заботать!». Мы опираемся на научные источники, "
        "но объясняем простым языком."
    )
    await message.answer(list_articles_text(session), reply_markup=markup)


@router.message(LibraryStates.reading, F.text.regexp(r'^\d+$'))
async def read_article_by_number(message: Message, state: FSMContext):
    current = await state.get_state()
    if current != LibraryStates.reading:
        return

    n = int(message.text.strip())
    session = Session()
    articles = get_ordered_articles(session)
    if n < 1 or n > len(articles):
        return await message.answer("⚠️ Статья с таким номером не найдена. Проверь список и номер.")

    article = articles[n - 1]
    date_str = article.date.strftime("%d.%m.%Y") if article.date else ""
    text = (
            f"📄 <b>{article.title}</b>\n\n"
            f"{article.description}\n\n"
            + (f"📅 {date_str}\n\n" if date_str else "")
            + f"🔗 {article.link}"
    )
    await message.answer(text, parse_mode="HTML")

@router.message(LibraryStates.reading, F.text == "⬅️ Назад")
async def back_from_library(message: Message, state: FSMContext):
    await state.clear()
    from app.keyboards import get_main_menu
    from app.utils.roles import get_user_role
    role = get_user_role(message.from_user.id)
    await message.answer("Главное меню:", reply_markup=get_main_menu(role))
