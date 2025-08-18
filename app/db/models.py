from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)

    grade = Column(Integer, nullable=True)
    subjects = Column(String, nullable=True)
    region = Column(String, nullable=True)
    username = Column(String, nullable=True)
    consent = Column(Boolean, default=False)
    role = Column(Integer, default=0, nullable=False)
    feedbacks = relationship("Feedback", back_populates="user")

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    link = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    text = Column(String, nullable=False)
    include_profile = Column(Boolean, default=False)
    read_by = Column(Text, default="")  # Список ID админов, прочитавших отзыв
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedbacks")
