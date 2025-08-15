from sqlalchemy import Column, Integer, String, Boolean
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
