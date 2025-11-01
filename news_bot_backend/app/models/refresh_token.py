from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String, Boolean
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models import User


class RefreshToken(Base):
    __tablename__ = "RefreshToken"

    id=Column(Integer, primary_key=True, autoincrement=True, index=True)
    hashed_token=Column(String(255), nullable=False)
    is_revoked=Column(Boolean, default=False)
    jti=Column(String, unique=True, nullable=False, index=True)

    user_id=Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    user=relationship("User", back_populates="refresh_tokens")

    created_at=Column(DateTime, nullable=False)
    expires_at=Column(DateTime, nullable=False)

