from sqlalchemy import Column, Integer, String, Date, Float
from db import Base

class Simulation(Base):
    __tablename__ = "simulations"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, nullable=True)  # can be version string or FK to strategies
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    sim_type = Column(String, nullable=True)
    rows_generated = Column(Integer, nullable=False)
    avg_hits = Column(Float, nullable=True)
    total_prize = Column(Float, nullable=True)
    roi = Column(Float, nullable=True)
    notes = Column(String, nullable=True) 