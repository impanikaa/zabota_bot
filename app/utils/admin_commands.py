# Команды для обычных админов
ADMIN_COMMANDS = {
    "/add_article": "Добавить статью (пошагово)",
    "/edit_art &lt;номер&gt;": "Редактировать статью",
    "/del_art &lt;номер&gt;": "Удалить статью",
    "/list_articles": "Показать список статей"
}

# Команды только для суперадмина
SUPERADMIN_COMMANDS = {
    "/add_admin &lt;id&gt;": "Добавить нового админа",
    "/remove_admin &lt;id&gt;": "Удалить админа",
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
