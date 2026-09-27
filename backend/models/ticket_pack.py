"""Ticket packs (purchase aid) and real-money ledger batches."""

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
)
from sqlalchemy.dialects.postgresql import JSON

from db import Base

PACK_STATUS_PENDING = "pending_purchase"
PACK_STATUS_SUBMITTED = "submitted"
PACK_STATUS_NOT_SUBMITTED = "not_submitted"


class TicketPack(Base):
    __tablename__ = "ticket_packs"

    id = Column(Integer, primary_key=True, index=True)
    target_draw_number = Column(Integer, nullable=True, index=True)
    target_draw_date = Column(Date, nullable=True)
    lines = Column(JSON, nullable=False)
    planned_cost_ils = Column(Numeric(10, 2), nullable=False)
    strategy_id = Column(String(160), nullable=True)
    main_algorithm = Column(String(80), nullable=False)
    strong_algorithm = Column(String(80), nullable=False)
    training_cutoff = Column(Date, nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(32), nullable=False, default=PACK_STATUS_PENDING)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=True)
    no_edge_label = Column(String(120), nullable=True)
    strategy_meta = Column(JSON, nullable=True)


class RealTicketBatch(Base):
    __tablename__ = "real_ticket_batches"

    id = Column(Integer, primary_key=True, index=True)
    ticket_pack_id = Column(Integer, ForeignKey("ticket_packs.id"), nullable=False, unique=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    investment_ils = Column(Numeric(10, 2), nullable=False)
    payout_ils = Column(Numeric(14, 2), nullable=True)
    net_ils = Column(Numeric(14, 2), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=False)
    settled_at = Column(DateTime(timezone=True), nullable=True)
    lines_snapshot = Column(JSON, nullable=False)


class PackDelivery(Base):
    __tablename__ = "pack_deliveries"

    id = Column(Integer, primary_key=True, index=True)
    ticket_pack_id = Column(Integer, ForeignKey("ticket_packs.id"), nullable=False, index=True)
    channel = Column(String(32), nullable=False)
    success = Column(Boolean, nullable=False)
    detail = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=False)
