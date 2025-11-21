from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.group import Group
from app.models.permission import Permission



class Articles(Base):
    __tablename__ = "Articles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    title = Column(String(255))
    summary = Column(Text)
    content = Column(Text, nullable=False)
    url = Column(String(512))
    image_url = Column(String(255))
    published_at = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    content_hash = Column(String(64), unique=True, index=True, nullable=False)
    sentiment_label = Column(String(32))
    sentiment_score = Column(Float)
    entities = Column(JSON, default=list)

    source_id = Column(Integer, ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"))
    source = relationship("Source", back_populates="articles")


