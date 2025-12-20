from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Topic(Base):
    __tablename__ = "Topic"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True)
    name=Column(String(50), nullable=False)

    sources = relationship("Source", back_populates="topic")
    articles = relationship("Articles", back_populates="topic")  # Добавляем обратную связь