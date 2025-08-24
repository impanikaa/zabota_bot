from app.db.models import User

def format_user_info(user: User, include_profile: bool) -> str:
    """Форматирует информацию о пользователе в одну строку"""
    if not user or not user.consent or not include_profile:
        return ""

    parts = []
    if user.username:
        parts.append(f"@{user.username}")
    if user.region:
        parts.append(user.region)
    if user.grade:
        parts.append(f"{user.grade} класс")
    if user.subjects:
        parts.append(user.subjects)

    return ", ".join(parts) if parts else ""