from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

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

class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    link = Column(String, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
