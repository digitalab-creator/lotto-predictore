from sqlalchemy import Column, Integer, String, DateTime, ARRAY, Boolean
from db import Base
import datetime

class GeneratedCombination(Base):
    __tablename__ = "generated_combinations"

    id = Column(Integer, primary_key=True, index=True)
    algorithm_id = Column(String, nullable=True)  # can be version string or FK to strategies
    generated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    numbers = Column(ARRAY(Integer), nullable=False)  # 6 numbers
    strong = Column(Integer, nullable=False)
    version = Column(String, nullable=False)
    used_in_real_draw = Column(Boolean, default=False) 