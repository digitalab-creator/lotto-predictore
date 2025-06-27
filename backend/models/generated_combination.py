from sqlalchemy import Column, Integer, DateTime, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
import datetime
from db.base import Base

class GeneratedCombination(Base):
    __tablename__ = "generated_combinations"

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey('predictions.id'), nullable=True)
    numbers = Column(ARRAY(Integer), nullable=False)  # 6 numbers
    strong_number = Column(Integer, nullable=False)
    position = Column(Integer, nullable=False)  # 1 = highest prob, 2 = next, etc.
    generated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    prediction = relationship("Prediction", back_populates="combinations") 