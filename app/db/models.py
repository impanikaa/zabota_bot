from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)       # Telegram ID
    username = Column(String)
    region = Column(String, nullable=True)
    grade = Column(Integer, nullable=True)            # Класс
    subjects = Column(String, nullable=True)          # Через запятую
    consent = Column(Boolean, default=False)          # Согласие
    role = Column(Integer, default=0)
