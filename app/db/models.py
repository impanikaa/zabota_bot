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
    read_by = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    request_type = Column(String, default='feedback')  # 'feedback', 'chat', 'question'
    # Для болталки:
    can_publish = Column(Boolean, default=True)
    is_published = Column(Boolean, default=False)
    post_link = Column(String, nullable=True)
    is_hidden = Column(Boolean, default=False)

    user = relationship("User", back_populates="feedbacks")


class UserReminder(Base):
    __tablename__ = "user_reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    type = Column(String)  # 'habit' или 'quote'
    habit_type = Column(String, nullable=True)  # Для предустановленных привычек
    custom_text = Column(String, nullable=True)  # Для кастомных привычек
    schedule_type = Column(String)  # 'fixed', 'interval', или 'random'
    times = Column(String, nullable=True)  # JSON для fixed времени
    interval_hours = Column(Integer, nullable=True)  # Для интервальных
    random_interval_hours = Column(Integer, nullable=True)  # Для случайных интервалов (в часах)
    start_time = Column(String, nullable=True)  # Начало периода отправки (может быть NULL)
    end_time = Column(String, nullable=True)  # Конец периода отправки (может быть NULL)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ReminderStat(Base):
    __tablename__ = "reminder_stats"

    id = Column(Integer, primary_key=True)
    reminder_id = Column(Integer, ForeignKey("user_reminders.id"))
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # 'sent', 'skipped_quiet_time', 'error'

    reminder = relationship("UserReminder")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    category = Column(String)  # Для категоризации цитат
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)