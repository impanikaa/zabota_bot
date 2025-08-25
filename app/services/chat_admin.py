from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from app.db.session import Session
from app.db.models import Feedback, User
from app.utils.roles import get_user_role
from app.config import ADMIN_IDS as ADMINS
from app.utils.format import format_user_info

router = Router()


class AdminChatStates(StatesGroup):
    waiting_chat_id = State()
    waiting_post_link = State()


class MarkPublishedStates(StatesGroup):
    waiting_chat_id = State()
    waiting_post_link = State()


class HideChatStates(StatesGroup):
    waiting_chat_id = State()


@router.message(F.text == "💬 Болталка")
async def chat_panel(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа к болталке.")

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Неопубликованные", callback_data="chat_unpublished")],
            [InlineKeyboardButton(text="📖 Все запросы", callback_data="chat_all")],
            [InlineKeyboardButton(text="👁️ Скрытые запросы", callback_data="chat_hidden")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="chat_back")]
        ]
    )
    await message.answer("💬 Панель болталки:", reply_markup=markup)


@router.callback_query(F.data == "chat_unpublished")
async def show_unpublished_chats(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id

    chats = session.query(Feedback).filter(
        Feedback.request_type == 'chat',
        Feedback.can_publish == True,
        Feedback.is_published == False,
        Feedback.is_hidden == False,
        ~Feedback.read_by.contains(str(admin_id))
    ).all()

    if not chats:
        return await call.message.edit_text("✅ Все запросы опубликованы или прочитаны!")

    text = "📝 <b>Неопубликованные запросы:</b>\n\n"
    for chat in chats:
        date_str = chat.created_at.strftime("%d.%m.%Y %H:%M")
        user = session.query(User).filter_by(user_id=chat.user_id).first()
        user_info = format_user_info(user, chat.include_profile)

        text += f"🆔 <b>ID {chat.id}</b> | 📅 {date_str}{f' | 👤 {user_info}' if user_info else ''}\n{chat.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "chat_all")
async def show_all_chats(call: CallbackQuery):
    session = Session()
    admin_id = call.from_user.id
    chats = session.query(Feedback).filter(
        Feedback.request_type == 'chat',
        Feedback.is_hidden == False
    ).all()

    if not chats:
        return await call.message.edit_text("❌ Запросов в болталке пока нет.")

    text = "📖 <b>Все запросы в болталке:</b>\n\n"
    for chat in chats:
        date_str = chat.created_at.strftime("%d.%m.%Y %H:%M")

        if not chat.can_publish:
            status = "🚫 Не для публикации"
        elif chat.is_published:
            status = "✅ Опубликовано"
        else:
            status = "📝 Ожидает публикации"

        user = session.query(User).filter_by(user_id=chat.user_id).first()
        user_info = format_user_info(user, chat.include_profile)

        text += f"{status} | 🆔 <b>ID {chat.id}</b> | 📅 {date_str}{f' | 👤 {user_info}' if user_info else ''}\n{chat.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "chat_hidden")
async def show_hidden_chats(call: CallbackQuery):
    session = Session()
    chats = session.query(Feedback).filter(
        Feedback.request_type == 'chat',
        Feedback.is_hidden == True
    ).all()

    if not chats:
        return await call.message.edit_text("❌ Скрытых запросов нет.")

    text = "👁️ <b>Скрытые запросы:</b>\n\n"
    for chat in chats:
        date_str = chat.created_at.strftime("%d.%m.%Y %H:%M")

        # Определяем статус запроса
        if not chat.can_publish:
            status = "🚫"
        elif chat.is_published:
            status = "✅"
        else:
            status = "📝"

        user = session.query(User).filter_by(user_id=chat.user_id).first()

        if chat.include_profile and user and user.consent:
            user_info = format_user_info(user, chat.include_profile)
            user_display = f"👤 {user_info}" if user_info else ""
        else:
            user_display = ""

        text += f"{status} 🆔 <b>ID {chat.id}</b> | 📅 {date_str}{f' | {user_display}' if user_display else ''}\n{chat.text}\n\n"

    await call.message.edit_text(text, parse_mode="HTML")


@router.callback_query(F.data == "chat_back")
async def back_from_chat(call: CallbackQuery):
    await call.message.edit_text("⬅️ Возврат в админку.")


@router.callback_query(F.data.startswith("mark_published_"))
async def mark_published_callback(call: CallbackQuery, state: FSMContext):
    chat_id = int(call.data.split("_")[-1])

    session = Session()
    chat = session.query(Feedback).get(chat_id)

    if not chat:
        await call.answer("Запрос не найден")
        return

    if chat.request_type != 'chat':
        await call.answer("Это не запрос болталки")
        return

    if not chat.can_publish:
        await call.answer("Этот запрос запрещено публиковать")
        return

    await state.update_data(chat_id=chat_id)
    await call.message.answer("Введи ссылку на опубликованный пост:")
    await state.set_state(MarkPublishedStates.waiting_post_link)

    await call.answer()


@router.message(MarkPublishedStates.waiting_post_link)
async def process_post_link(message: Message, state: FSMContext):
    post_link = message.text.strip()
    data = await state.get_data()
    chat_id = data.get("chat_id")

    session = Session()
    chat = session.query(Feedback).get(chat_id)

    if chat:
        chat.is_published = True
        chat.post_link = post_link
        session.commit()

        # Отправляем уведомление пользователю
        try:
            await message.bot.send_message(
                chat_id=chat.user_id,
                text=f"💬 Твой запрос в #болталку был опубликован! В комментариях тебе обязательно помогут.\n\nСсылка на пост: {post_link}"
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление пользователю {chat.user_id}: {e}")

        await message.answer(f"✅ Запрос ID {chat_id} отмечен как опубликованный и пользователь уведомлен!")
    else:
        await message.answer("❌ Запрос не найден.")

    await state.clear()


@router.message(F.text == "/mark_published")
async def start_mark_published(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав для этой команды.")

    await message.answer("Введи ID запроса, который хочешь отметить как опубликованный:")
    await state.set_state(MarkPublishedStates.waiting_chat_id)


@router.message(MarkPublishedStates.waiting_chat_id)
async def process_mark_published(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    session = Session()
    chat = session.query(Feedback).get(chat_id)

    if not chat:
        await message.answer("❌ Запрос с таким ID не найден.")
        await state.clear()
        return

    if chat.request_type != 'chat':
        await message.answer("❌ Это не запрос болталки, нельзя отметить как опубликованный.")
        await state.clear()
        return

    if not chat.can_publish:
        await message.answer("❌ Этот запрос запрещено публиковать.")
        await state.clear()
        return

    await state.update_data(chat_id=chat_id)
    await message.answer("Введи ссылку на опубликованный пост:")
    await state.set_state(MarkPublishedStates.waiting_post_link)


@router.message(F.text == "📝 Отметить опубликованным")
async def mark_published_button(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав.")

    await message.answer("Введи ID запроса, который хочешь отметить как опубликованный:")
    await state.set_state(MarkPublishedStates.waiting_chat_id)


@router.message(F.text.startswith("/hide_chat"))
async def hide_chat_command(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет прав для этой команды.")

    try:
        chat_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("❌ Использование: /hide_chat <ID>")
        return

    session = Session()
    chat = session.query(Feedback).get(chat_id)

    if not chat:
        await message.answer("❌ Запрос с таким ID не найден.")
        return

    if chat.request_type != 'chat':
        await message.answer("❌ Это не запрос болталки, нельзя скрыть.")
        return

    chat.is_hidden = True
    session.commit()

    await message.answer(f"✅ Запрос ID {chat_id} скрыт!")


@router.message(HideChatStates.waiting_chat_id)
async def process_hide_chat(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID должен быть числом. Попробуй еще раз.")
        return

    session = Session()
    chat = session.query(Feedback).get(chat_id)

    if not chat:
        await message.answer("❌ Запрос с таким ID не найден.")
        await state.clear()
        return

    if chat.request_type != 'chat':
        await message.answer("❌ Это не запрос болталки, нельзя скрыть.")
        await state.clear()
        return

    chat.is_hidden = True
    session.commit()

    await message.answer(f"✅ Запрос ID {chat_id} скрыт!")
    await state.clear()
