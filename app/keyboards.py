from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu(role: int):
    base = [
        [KeyboardButton(text="📚 Библиотека")],
        [KeyboardButton(text="⏰ Напоминания")],
        [KeyboardButton(text="💬 Поддержка")],
        [KeyboardButton(text="ℹ️ О проекте")],
    ]
    if role >= 1:
        base.append([KeyboardButton(text="🛠 Админка")])
    return ReplyKeyboardMarkup(keyboard=base, resize_keyboard=True)


def get_support_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="🙏 #болталка")],
            [KeyboardButton(text="📝 Отзыв")],
            [KeyboardButton(text="❓ Вопрос администрации")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )
