from datetime import datetime

from sqlalchemy import Column, Integer, Boolean, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class User(Base):
    __tablename__ = "User"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    username = Column(String(30), unique=True, nullable=False)
    first_name = Column(String(20))
    last_name = Column(String(30))
    email = Column(String(50), unique=True, nullable=False)
    profile_photo = Column(String(255))
    is_verified = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    bio = Column(Text)
    scan_period = Column(Integer, default=3)
    hashed_password = Column(String(255), nullable=False)

    articles = relationship("Articles", back_populates="user")
