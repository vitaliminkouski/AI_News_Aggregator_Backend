from sqlalchemy import Column, Integer, VARCHAR

from app.db.database import Base

class TestTable(Base):

    __tablename__ = "TestTable"
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    name = Column(VARCHAR(100), index=True, nullable=False)