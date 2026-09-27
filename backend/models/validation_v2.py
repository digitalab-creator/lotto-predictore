"""Sealed go/no-go rows. The holdout table accepts one result, ever."""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql import func

from db import Base


class ValidationExperiment(Base):
    __tablename__ = "validation_experiments"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    regime_start = Column(Date, nullable=False)
    select_start_date = Column(Date, nullable=False)
    holdout_start_date = Column(Date, nullable=False)
    holdout_end_date = Column(Date, nullable=False)
    draw_count = Column(Integer, nullable=False)
    git_sha = Column(String(40), nullable=True)
    status = Column(String(40), nullable=False)
    refusal_reason = Column(Text, nullable=True)


class ValidationLock(Base):
    __tablename__ = "validation_locks"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("validation_experiments.id"), nullable=False, unique=True)
    main_algorithm = Column(String(80), nullable=False)
    strong_algorithm = Column(String(80), nullable=False)
    strategy_id = Column(String(160), nullable=False)
    primary_rate = Column(Numeric(12, 8), nullable=False)
    first_half_rate = Column(Numeric(12, 8), nullable=False)
    second_half_rate = Column(Numeric(12, 8), nullable=False)
    promoted = Column(Boolean, nullable=False, default=False)
    candidate_scores = Column(JSON, nullable=False)
    locked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ValidationHoldoutResult(Base):
    """``seal`` is always 1, so the database itself rejects a second holdout."""

    __tablename__ = "validation_holdout_results"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("validation_experiments.id"), nullable=False, unique=True)
    seal = Column(Integer, nullable=False, unique=True, default=1)
    verdict = Column(String(32), nullable=False)
    report = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ValidationStep(Base):
    __tablename__ = "validation_steps"
    __table_args__ = (
        UniqueConstraint("experiment_id", "stage", "strategy_id", "draw_date", name="uq_validation_step"),
    )

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("validation_experiments.id"), nullable=False, index=True)
    stage = Column(String(16), nullable=False)
    strategy_id = Column(String(160), nullable=False)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    draw_date = Column(Date, nullable=False)
    lines = Column(JSON, nullable=False)
    ticket_wins = Column(Integer, nullable=False)
    line_count = Column(Integer, nullable=False)
    tier_counts = Column(JSON, nullable=False)
    mean_main_hits = Column(Numeric(8, 4), nullable=False)
    payout_ils = Column(Numeric(14, 2), nullable=True)
    cost_ils = Column(Numeric(14, 2), nullable=True)
    random_ticket_rate = Column(Numeric(12, 8), nullable=True)


class ShadowCommitment(Base):
    """Lines sealed before the draw. A database trigger rejects updates and deletes."""

    __tablename__ = "shadow_commitments"

    id = Column(Integer, primary_key=True)
    lines = Column(JSON, nullable=False)
    lines_hash = Column(String(64), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    git_sha = Column(String(40), nullable=False)
    main_algorithm = Column(String(80), nullable=False)
    strong_algorithm = Column(String(80), nullable=False)
    training_cutoff = Column(Date, nullable=False)
    target_draw_number = Column(Integer, nullable=True, index=True)
    ticket_pack_id = Column(Integer, ForeignKey("ticket_packs.id"), nullable=True)


class ShadowOutcome(Base):
    __tablename__ = "shadow_outcomes"

    id = Column(Integer, primary_key=True)
    commitment_id = Column(Integer, ForeignKey("shadow_commitments.id"), nullable=False, unique=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=False)
    settled_at = Column(DateTime(timezone=True), nullable=False)
    winning_lines = Column(Integer, nullable=False)
    payout_ils = Column(Numeric(14, 2), nullable=True)
    cost_ils = Column(Numeric(14, 2), nullable=True)
    detail = Column(JSON, nullable=False)


class CoveragePortfolio(Base):
    __tablename__ = "coverage_portfolios"

    id = Column(Integer, primary_key=True)
    regime_start = Column(Date, nullable=False, index=True)
    lines = Column(JSON, nullable=False)
    p_any = Column(Numeric(12, 8), nullable=False)
    report = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
