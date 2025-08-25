from app.db.session import Session
from app.db.models import User
from app.config import OWNER_ID, ADMIN_IDS

def get_user_role(user_id: int) -> int:
    if user_id == OWNER_ID:
        return 2

    if user_id in ADMIN_IDS:
        return 1

    # Для обычных пользователей проверяем роль в базе
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    return user.role if user else 0