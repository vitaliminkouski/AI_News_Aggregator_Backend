from datetime import datetime

from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.group import Group
from app.models.permission import Permission
from app.models.source import Source
from app.models.user import User


class Articles(Base):
    __tablename__ = "Articles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    title = Column(String(50))
    summary = Column(Text)
    image_url=Column(String(255))
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    source_id = Column(Integer, ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"))
    source = relationship(Source)

    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    user = relationship(User, back_populates="articles")
