# app/handlers/library_admin.py
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from datetime import datetime

from app.db.session import Session
from app.db.models import Article
from app.utils.roles import get_user_role

router = Router()

# States
class AddArticleStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_link = State()
    waiting_for_date = State()

class EditArticleStates(StatesGroup):
    waiting_for_field = State()
    waiting_for_value = State()

# Helpers
def get_ordered_articles(session):
    return session.query(Article).order_by(Article.date.asc(), Article.id.asc()).all()

def list_articles_text(session) -> str:
    articles = get_ordered_articles(session)
    if not articles:
        return "📚 В библиотеке пока нет статей."
    text = "📚 Список статей:\n\n"
    for idx, a in enumerate(articles, start=1):
        text += f"{idx}. {a.title}\n"
    return text

# === Add article (step-by-step) ===
@router.message(Command("add_article"))
async def add_article_start(message: Message, state: FSMContext):
    if get_user_role(message.from_user.id) < 1:
        return await message.answer("⛔ У тебя нет прав.")
    await message.answer("📝 Введи заголовок статьи:")
    await state.set_state(AddArticleStates.waiting_for_title)

@router.message(AddArticleStates.waiting_for_title)
async def add_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("✍️ Введи краткое описание:")
    await state.set_state(AddArticleStates.waiting_for_description)

@router.message(AddArticleStates.waiting_for_description)
async def add_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text.strip())
    await message.answer("🔗 Введи ссылку на статью (Telegra.ph):")
    await state.set_state(AddArticleStates.waiting_for_link)

@router.message(AddArticleStates.waiting_for_link)
async def add_link(message: Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await message.answer("📅 Введи дату публикации в формате YYYY-MM-DD (например 2025-03-22):")
    await state.set_state(AddArticleStates.waiting_for_date)

@router.message(AddArticleStates.waiting_for_date)
async def add_date(message: Message, state: FSMContext):
    txt = message.text.strip()
    try:
        dt = datetime.strptime(txt, "%Y-%m-%d")
    except ValueError:
        return await message.answer("❌ Неверный формат даты. Используй YYYY-MM-DD.")
    data = await state.get_data()
    session = Session()
    article = Article(
        title=data["title"],
        description=data["description"],
        link=data["link"],
        date=dt
    )
    session.add(article)
    session.commit()
    await state.clear()
    await message.answer("✅ Статья добавлена!\n\n" + list_articles_text(session))

# === Delete article ===
@router.message(Command("del_art"))
async def delete_article(message: Message):
    if get_user_role(message.from_user.id) < 1:
        return await message.answer("⛔ У тебя нет прав.")
    parts = message.text.split()
    session = Session()
    if len(parts) < 2:
        return await message.answer("❗ Укажи номер статьи для удаления.\n\n" + list_articles_text(session))
    try:
        num = int(parts[1])
    except ValueError:
        return await message.answer("❌ Номер должен быть целым числом.")
    articles = get_ordered_articles(session)
    if num < 1 or num > len(articles):
        return await message.answer("❌ Статья с таким номером не найдена.")
    article = articles[num-1]
    session.delete(article)
    session.commit()
    await message.answer("🗑 Статья удалена.\n\n" + list_articles_text(session))

# === Edit article (command) ===
@router.message(Command("edit_art"))
async def edit_art_start(message: Message, state: FSMContext):
    if get_user_role(message.from_user.id) < 1:
        return await message.answer("⛔ У тебя нет прав.")
    parts = message.text.split()
    session = Session()
    if len(parts) < 2:
        return await message.answer("❗ Укажи номер статьи для редактирования.\n\n" + list_articles_text(session))
    try:
        num = int(parts[1])
    except ValueError:
        return await message.answer("❌ Номер должен быть целым числом.")
    articles = get_ordered_articles(session)
    if num < 1 or num > len(articles):
        return await message.answer("❌ Статья с таким номером не найдена.")
    article = articles[num-1]
    await state.update_data(article_id=article.id)
    await state.set_state(EditArticleStates.waiting_for_field)
    await message.answer("Что редактируем? Введи одно из: title / description / link / date")

@router.message(EditArticleStates.waiting_for_field)
async def edit_field(message: Message, state: FSMContext):
    fld = message.text.strip().lower()
    if fld not in ("title", "description", "link", "date"):
        return await message.answer("❌ Доступные поля: title, description, link, date")
    await state.update_data(field=fld)
    await state.set_state(EditArticleStates.waiting_for_value)
    await message.answer(f"Введи новое значение для поля {fld}:")

@router.message(EditArticleStates.waiting_for_value)
async def edit_value(message: Message, state: FSMContext):
    data = await state.get_data()
    session = Session()
    article = session.query(Article).filter_by(id=data["article_id"]).first()
    if not article:
        await state.clear()
        return await message.answer("❌ Статья не найдена.")
    field = data["field"]
    new_raw = message.text.strip()
    if field == "date":
        try:
            new_dt = datetime.strptime(new_raw, "%Y-%m-%d")
        except ValueError:
            return await message.answer("❌ Неверный формат даты. Используй YYYY-MM-DD.")
        article.date = new_dt
    else:
        setattr(article, field, new_raw)
    session.commit()
    await state.clear()
    await message.answer("✅ Статья обновлена.\n\n" + list_articles_text(session))
