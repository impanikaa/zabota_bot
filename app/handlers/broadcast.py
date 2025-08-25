from aiogram import Router, F, Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from app.db.session import Session
from app.db.models import User
from app.keyboards import get_main_menu
from app.utils.roles import get_user_role
import asyncio
import logging

logger = logging.getLogger(__name__)
router = Router()


class BroadcastStates(StatesGroup):
    message = State()


@router.message(F.text == "📢 Рассылка")
async def broadcast_start(message: Message, state: FSMContext):
    role = get_user_role(message.from_user.id)
    if role < 1:
        return await message.answer("⛔ Недостаточно прав")

    await message.answer("Отправьте сообщение для рассылки:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(BroadcastStates.message)


@router.message(BroadcastStates.message)
async def broadcast_message(message: Message, state: FSMContext, bot: Bot):
    session = Session()
    # Получаем ВСЕХ пользователей, не только тех, кто дал согласие
    users = session.query(User).all()

    success = 0
    failed = 0

    if not users:
        await message.answer("❌ Нет пользователей для рассылки")
        await state.clear()
        return

    # Отправляем сообщение о начале рассылки
    progress_msg = await message.answer(f"📤 Начинаем рассылку для {len(users)} пользователей...")

    for user in users:
        try:
            # Используем copy_message для сохранения форматирования
            await bot.copy_message(
                chat_id=user.user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception as e:
            failed += 1
            logger.error(f"Ошибка при отправке пользователю {user.user_id}: {e}")

        # Обновляем сообщение о прогрессе каждые 5 отправок
        if (success + failed) % 5 == 0:
            try:
                await progress_msg.edit_text(
                    f"📤 Рассылка в процессе...\n"
                    f"Успешно: {success}\n"
                    f"Не удалось: {failed}\n"
                    f"Осталось: {len(users) - success - failed}"
                )
            except:
                pass

        await asyncio.sleep(0.1)  # Задержка между отправками

    # Удаляем сообщение о прогрессе
    try:
        await progress_msg.delete()
    except:
        pass

    await message.answer(
        f"✅ Рассылка завершена\n"
        f"Успешно: {success}\n"
        f"Не удалось: {failed}",
        reply_markup=get_main_menu(get_user_role(message.from_user.id))
    )
    await state.clear()