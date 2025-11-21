from datetime import datetime

from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Source(Base):
    __tablename__="Source"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    source_name=Column(String(100))
    source_url=Column(String(255), nullable=False)
    language=Column(String(2))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    topic_id=Column(Integer, ForeignKey("Topic.id", ondelete="CASCADE", onupdate="CASCADE"))
    topic=relationship("Topic", back_populates="sources")

    user_sources = relationship("UserSources", back_populates="source")
    articles=relationship("Articles", back_populates="source")

