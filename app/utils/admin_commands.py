ADMIN_COMMANDS = {
    "/add_article": "Добавить статью (пошагово)",
    "/edit_art [номер]": "Редактировать статью",
    "/del_art [номер]": "Удалить статью",
    "/list_articles": "Показать список статей",
    "/mark_read [ID]": "Отметить отзыв прочитанным",
    "/hide_feedback [ID]": "Скрыть отзыв",
    "/mark_published [ID]": "Отметить запрос болталки опубликованным",
    "/hide_chat [ID]": "Скрыть запрос болталки",
    "/hide_question [ID]": "Скрыть вопрос администрации",
    "/add_quote": "Добавить цитату (пошагово)",
    "/list_quotes": "Показать список цитат",
    "/quote_stats": "Статистика цитат"
}

SUPERADMIN_COMMANDS = {
    "/add_admin [id]": "Добавить нового админа",
    "/remove_admin [id]": "Удалить админа",
    "/list_admins": "Показать список всех админов"
}

def format_admin_commands(is_superadmin: bool = False) -> str:
    text = "📋 <b>Команды администратора:</b>\n\n"
    for cmd, desc in ADMIN_COMMANDS.items():
        text += f"{cmd} — {desc}\n"

    if is_superadmin:
        text += "\n👑 <b>Команды суперадмина:</b>\n\n"
        for cmd, desc in SUPERADMIN_COMMANDS.items():
            text += f"{cmd} — {desc}\n"

    return text