"""pais csv prize columns, quarantine, ingest state

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("draws", "jackpot", new_column_name="jackpot_lotto")
    op.add_column("draws", sa.Column("jackpot_double", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("total_prizes", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("winners_per_tier", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("draws", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "ingest_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("csv_sha256", sa.String(length=64), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("integrity_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("integrity_reason", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "draw_quarantine",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("draw_number", sa.Integer(), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("raw_row", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_draw_quarantine_draw_number", "draw_quarantine", ["draw_number"])


def downgrade() -> None:
    op.drop_index("ix_draw_quarantine_draw_number", table_name="draw_quarantine")
    op.drop_table("draw_quarantine")
    op.drop_table("ingest_state")
    op.drop_column("draws", "verified_at")
    op.drop_column("draws", "winners_per_tier")
    op.drop_column("draws", "total_prizes")
    op.drop_column("draws", "jackpot_double")
    op.alter_column("draws", "jackpot_lotto", new_column_name="jackpot")
