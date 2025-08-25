from aiogram.filters import BaseFilter
from aiogram.types import Message
from app.db.session import Session
from app.db.models import User


class RoleFilter(BaseFilter):
    def __init__(self, min_role: int):
        self.min_role = min_role

    async def __call__(self, message: Message) -> bool:
        session = Session()
        user = session.query(User).filter_by(user_id=message.from_user.id).first()
        return user is not None and user.role >= self.min_role
