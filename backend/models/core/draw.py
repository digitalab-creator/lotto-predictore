from sqlalchemy import Column, Integer, Date, ARRAY
from db.base import Base

class Draw(Base):
    __tablename__ = "draws"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    numbers = Column(ARRAY(Integer), nullable=False)  # 6 numbers
    strong_number = Column(Integer, nullable=False) 