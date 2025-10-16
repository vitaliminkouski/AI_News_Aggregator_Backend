from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text

from app.db.database import Base


class Topic(Base):
    __tablename__ = "Topic"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    name=Column(String(255), nullable=False)