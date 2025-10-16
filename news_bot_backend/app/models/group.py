import uuid
from datetime import datetime

from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.user import User


class Group(Base):
    __tablename__="Group"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    name=Column(String(100), nullable=False)

    owner_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    owner = relationship(User, back_populates="hosted_groups")

    scan_period=Column(Integer, default=3)
    created_at=Column(DateTime, default=datetime.utcnow)
    invite_token=Column(String(36), default=lambda: str(uuid.uuid4()))
