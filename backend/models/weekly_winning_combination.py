from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON, Float, Date
from sqlalchemy.orm import relationship
import datetime
from db.base import Base

class WeeklyWinningCombination(Base):
    __tablename__ = "weekly_winning_combinations"

    id = Column(Integer, primary_key=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    strong_model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    main_model_params = Column(JSON, nullable=True)
    strong_model_params = Column(JSON, nullable=True)
    total_roi = Column(Float, nullable=False)
    num_prediction_runs = Column(Integer, nullable=False)
    num_tickets = Column(Integer, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_prize = Column(Float, nullable=False)
    week_start_date = Column(Date, nullable=False)
    week_end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    model = relationship("Model", foreign_keys=[model_id])
    strong_model = relationship("Model", foreign_keys=[strong_model_id]) 