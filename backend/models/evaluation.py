"""Walk-forward evaluation scoreboard (Phase 4) — separate from legacy predictions."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSON

from db import Base


class EvaluationTicket(Base):
    """One scored line from an expanding-window walk-forward step."""

    __tablename__ = "evaluation_tickets"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(160), nullable=False, index=True)
    algorithm_version = Column(String(80), nullable=False)
    strong_algorithm_version = Column(String(80), nullable=False)
    git_sha = Column(String(40), nullable=True)
    params = Column(JSON, nullable=True)
    seed = Column(Integer, nullable=True)
    training_cutoff = Column(Date, nullable=False, index=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=False, index=True)
    line_index = Column(Integer, nullable=False)
    numbers = Column(ARRAY(Integer), nullable=False)
    strong_number = Column(Integer, nullable=False)
    payout_ils = Column(Numeric(14, 2), nullable=False, default=0)
    cost_ils = Column(Numeric(8, 2), nullable=False, default=0)
    net_ils = Column(Numeric(14, 2), nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    strong_hit = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=True)


class StrategySummary(Base):
    """Aggregated walk-forward metrics per main+strong strategy."""

    __tablename__ = "strategy_summaries"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String(160), nullable=False, unique=True, index=True)
    algorithm_version = Column(String(80), nullable=False)
    strong_algorithm_version = Column(String(80), nullable=False)
    git_sha = Column(String(40), nullable=True)
    params = Column(JSON, nullable=True)
    roi = Column(Numeric(14, 6), nullable=True)
    mean_payout_per_line = Column(Numeric(14, 4), nullable=True)
    median_payout_per_line = Column(Numeric(14, 4), nullable=True)
    hit_rate_3plus = Column(Numeric(10, 6), nullable=True)
    strong_accuracy = Column(Numeric(10, 6), nullable=True)
    max_drawdown = Column(Numeric(14, 6), nullable=True)
    variance_net = Column(Numeric(18, 6), nullable=True)
    random_percentile = Column(Numeric(8, 4), nullable=True)
    bootstrap_roi_p5 = Column(Numeric(14, 6), nullable=True)
    bootstrap_roi_p95 = Column(Numeric(14, 6), nullable=True)
    random_baseline_median_roi = Column(Numeric(14, 6), nullable=True)
    random_baseline_p5 = Column(Numeric(14, 6), nullable=True)
    random_baseline_p95 = Column(Numeric(14, 6), nullable=True)
    independent_draw_count = Column(Integer, nullable=False, default=0)
    has_predictive_edge = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
