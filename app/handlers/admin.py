from aiogram import Router
from aiogram.types import Message
from app.filters.role import RoleFilter

router = Router()

@router.message(RoleFilter(min_role=1))  # админы и выше
async def admin_menu(message: Message):
    await message.answer("Добро пожаловать в админку 🛠")

@router.message(RoleFilter(min_role=2))  # только владелец
async def owner_panel(message: Message):
    await message.answer("Это суперадминка 👑")
