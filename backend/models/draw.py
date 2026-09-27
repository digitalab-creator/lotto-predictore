from sqlalchemy import Column, Integer, Date, ARRAY, Numeric, String, DateTime
from sqlalchemy.dialects.postgresql import JSON

from db import Base


class Draw(Base):
    __tablename__ = "draws"

    id = Column(Integer, primary_key=True, index=True)
    draw_number = Column(Integer, nullable=True, unique=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    numbers = Column(ARRAY(Integer), nullable=False)
    strong_number = Column(Integer, nullable=False)

    prize_6_strong = Column(Numeric(14, 2), nullable=True)
    prize_6 = Column(Numeric(14, 2), nullable=True)
    prize_5_strong = Column(Numeric(14, 2), nullable=True)
    prize_5 = Column(Numeric(14, 2), nullable=True)
    prize_4_strong = Column(Numeric(14, 2), nullable=True)
    prize_4 = Column(Numeric(14, 2), nullable=True)
    prize_3_strong = Column(Numeric(14, 2), nullable=True)
    prize_3 = Column(Numeric(14, 2), nullable=True)
    jackpot_lotto = Column(Numeric(14, 2), nullable=True)
    jackpot_double = Column(Numeric(14, 2), nullable=True)
    total_prizes = Column(Numeric(14, 2), nullable=True)
    winners_per_tier = Column(JSON, nullable=True)
    ticket_cost_ils = Column(Numeric(8, 2), nullable=True)
    source = Column(String(32), nullable=True)
    source_hash = Column(String(64), nullable=True)
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
