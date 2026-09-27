"""Rows that are not a draw: one ingest bookmark, and rejected CSV lines."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from db import Base


class IngestState(Base):
    """Single row (id=1). The CSV hash skips a repeat of a file that did not change."""

    __tablename__ = "ingest_state"

    id = Column(Integer, primary_key=True)
    csv_sha256 = Column(String(64), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    integrity_blocked = Column(Boolean, nullable=False, default=False)
    integrity_reason = Column(String(500), nullable=True)


class DrawQuarantine(Base):
    """A CSV line we refused to write. The draws table is left as it was."""

    __tablename__ = "draw_quarantine"

    id = Column(Integer, primary_key=True)
    draw_number = Column(Integer, nullable=True, index=True)
    reason = Column(String(200), nullable=False)
    raw_row = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
