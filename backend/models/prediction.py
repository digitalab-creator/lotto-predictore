from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Text, Date, JSON
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
    main_model_params = Column(JSON, nullable=True)
    strong_model_params = Column(JSON, nullable=True)
    model = relationship("Model", foreign_keys=[model_id])
    strong_model = relationship("Model", foreign_keys=[strong_model_id])
    combinations = relationship("GeneratedCombination", back_populates="prediction")
    details = relationship("PredictionDetail", back_populates="prediction", cascade="all, delete-orphan")

class PredictionDetail(Base):
    __tablename__ = "prediction_details"
    id = Column(Integer, primary_key=True)
    prediction_id = Column(Integer, ForeignKey('predictions.id'), nullable=False)
    test_draw_date = Column(Date, nullable=False)
    actual_numbers = Column(JSON, nullable=False)
    actual_strong = Column(Integer, nullable=True)
    predicted_numbers = Column(JSON, nullable=False)
    predicted_strong = Column(Integer, nullable=True)
    hits = Column(Integer, nullable=False)
    strong_hit = Column(Integer, nullable=False)
    prize = Column(Float, nullable=False)
    roi = Column(Float, nullable=False)
    prediction = relationship("Prediction", back_populates="details") 