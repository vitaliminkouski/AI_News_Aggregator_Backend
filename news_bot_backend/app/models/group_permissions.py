from datetime import datetime

from sqlalchemy import Column, Integer, VARCHAR, Boolean, DateTime, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.group import Group
from app.models.permission import Permission
from app.models.user import User


class GroupPermissions(Base):
    __tablename__="GroupPermissions"
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', 'permission_id', name='uq_user_group_permission'),
    )

    id=Column(Integer, primary_key=True, autoincrement=True, index=True, unique=True)

    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"))
    user = relationship(User)

    group_id = Column(Integer, ForeignKey("Group.id", ondelete="CASCADE", onupdate="CASCADE"))
    group = relationship(Group)

    permission_id = Column(Integer, ForeignKey("Permission.id", ondelete="CASCADE", onupdate="CASCADE"))
    permission = relationship(Permission)