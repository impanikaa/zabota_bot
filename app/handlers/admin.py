from aiogram import Router, F
from aiogram.types import Message
from app.utils.roles import get_user_role
from app.utils.admin_commands import format_admin_commands

router = Router()


@router.message(F.text == "🛠 Админка")
async def admin_panel(message: Message):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ У тебя нет доступа к админке.")

    text = format_admin_commands(is_superadmin=(role == 2))
    await message.answer(text, parse_mode="HTML")

