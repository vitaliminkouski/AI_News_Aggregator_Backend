from sqlalchemy import Column, Integer, String

from app.db.database import Base


class Permission(Base):
    __tablename__ = 'Permission'
    id=Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)
    name=Column(String(10), unique=True, nullable=False)
