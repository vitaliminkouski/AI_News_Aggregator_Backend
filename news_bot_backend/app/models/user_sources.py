from collections import defaultdict
from datetime import datetime
from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base


class UserSources(Base):
    __tablename__="UserSources"
    __table_args__ = (
        UniqueConstraint('user_id', 'source_id', name='uq_user_source'),
    )

    id=Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    subscribed_at=Column(DateTime, default=datetime.utcnow)

    user_id=Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    user=relationship("User", back_populates="user_sources")

    source_id=Column(Integer, ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"))
    source=relationship("Source", back_populates="user_sources")

