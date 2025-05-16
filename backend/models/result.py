from sqlalchemy import Column, Integer, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from db import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    combination_id = Column(Integer, ForeignKey('generated_combinations.id'), nullable=False)
    draw_id = Column(Integer, ForeignKey('draws.id'), nullable=False)
    hits = Column(Integer, nullable=False)
    strong_hit = Column(Boolean, nullable=False)
    prize = Column(Float, nullable=True)

    combination = relationship("GeneratedCombination")
    draw = relationship("Draw") 