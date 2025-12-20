from datetime import datetime, timezone

from sqlalchemy import Column, Integer, DateTime, String, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.group import Group
from app.models.permission import Permission



class Articles(Base):
    __tablename__ = "Articles"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    title = Column(String(255), index=True)
    summary = Column(Text)
    image_url = Column(String(255))
    url=Column(String(255), unique=True)
    published_at = Column(DateTime)
    fetched_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    sentiment_label = Column(String(32))
    sentiment_score = Column(Float)
    entities = Column(JSON, default=list)

    source_id = Column(Integer, ForeignKey("Source.id", ondelete="CASCADE", onupdate="CASCADE"))
    source = relationship("Source", back_populates="articles")
    
    topic_id = Column(Integer, ForeignKey("Topic.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    topic = relationship("Topic", back_populates="articles")


