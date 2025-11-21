from datetime import datetime

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String, Boolean, UUID
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models import User


class RefreshToken(Base):
    __tablename__ = "RefreshToken"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True)
    hashed_token=Column(String(255), nullable=False)
    is_revoked=Column(Boolean, default=False)
    jti=Column(UUID, unique=True, nullable=False, index=True)

    user_id=Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    user=relationship("User", back_populates="refresh_tokens")

    created_at=Column(DateTime, default=datetime.utcnow)
    expires_at=Column(DateTime(timezone=True), default=datetime.utcnow)

