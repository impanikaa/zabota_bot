import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message

from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("Привет! Я бот проекта «Заботать!». Готов поддерживать тебя :)")

async def main():
    print("Бот запускается...")
    await dp.start_polling(bot)
    print("Бот запущен!")

if __name__ == "__main__":
    asyncio.run(main())
