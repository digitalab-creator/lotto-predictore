from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
import datetime
from db.base import Base

class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    strong_model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    run_time = Column(DateTime, default=datetime.datetime.utcnow)
    roi = Column(Float, nullable=False)
    total_prize = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    test_count = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    train_start_date = Column(Date, nullable=False)
    train_end_date = Column(Date, nullable=False)
    num_test_draws = Column(Integer, nullable=False)
    top_n_per_position = Column(Integer, nullable=False)
    model = relationship("Model", foreign_keys=[model_id])
    strong_model = relationship("Model", foreign_keys=[strong_model_id])
    combinations = relationship("GeneratedCombination", back_populates="prediction") 