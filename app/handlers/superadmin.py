from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.db.session import Session
from app.db.models import User
from app.config import OWNER_ID, ADMIN_IDS
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("add_admin"))
async def add_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("⛔ Только владелец может добавлять админов")

    try:
        admin_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        return await message.answer("Использование: /add_admin [user_id]")

    session = Session()
    user = session.query(User).filter_by(user_id=admin_id).first()
    if user:
        user.role = 1
        session.commit()
        # Добавляем в конфиг
        if admin_id not in ADMIN_IDS:
            ADMIN_IDS.append(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} стал админом")
    else:
        # Если пользователя нет в базе, создаем его
        new_user = User(user_id=admin_id, role=1)
        session.add(new_user)
        session.commit()
        if admin_id not in ADMIN_IDS:
            ADMIN_IDS.append(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} добавлен в базу и стал админом")


@router.message(Command("remove_admin"))
async def remove_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("⛔ Только владелец может удалять админов")

    try:
        admin_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        return await message.answer("Использование: /remove_admin [user_id]")

    session = Session()
    user = session.query(User).filter_by(user_id=admin_id).first()
    if user and user.role == 1:
        user.role = 0
        session.commit()
        # Удаляем из конфига
        if admin_id in ADMIN_IDS:
            ADMIN_IDS.remove(admin_id)
        await message.answer(f"✅ Пользователь {admin_id} больше не админ")
    else:
        await message.answer("❌ Пользователь не найден или не является админом")


@router.message(Command("list_admins"))
async def list_admins(message: Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("⛔ Только владелец может просматривать список админов")

    session = Session()
    # Получаем всех пользователей с ролью >= 1 (админы и владелец)
    admins = session.query(User).filter(User.role >= 1).all()

    if not admins:
        await message.answer("❌ В системе нет администраторов")
        return

    admin_list = ["👑 Владелец и администраторы:"]

    for admin in admins:
        if admin.user_id == OWNER_ID:
            role_text = "Владелец"
        else:
            role_text = "Админ"
        username = f"@{admin.username}" if admin.username else "нет username"
        admin_list.append(f"• {role_text}: {admin.user_id} ({username})")

    await message.answer("\n".join(admin_list))