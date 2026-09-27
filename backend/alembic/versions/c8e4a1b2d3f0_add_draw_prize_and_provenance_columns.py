"""add draw prize and provenance columns

Revision ID: c8e4a1b2d3f0
Revises: add_training_params
Create Date: 2026-04-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8e4a1b2d3f0"
down_revision: Union[str, None] = "add_training_params"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("draws", sa.Column("draw_number", sa.Integer(), nullable=True))
    op.add_column("draws", sa.Column("prize_6_strong", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_6", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_5_strong", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_5", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_4_strong", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_4", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_3_strong", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("prize_3", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("jackpot", sa.Numeric(14, 2), nullable=True))
    op.add_column("draws", sa.Column("ticket_cost_ils", sa.Numeric(8, 2), nullable=True))
    op.add_column("draws", sa.Column("source", sa.String(length=32), nullable=True))
    op.add_column("draws", sa.Column("source_hash", sa.String(length=64), nullable=True))
    op.add_column("draws", sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_draws_draw_number"), "draws", ["draw_number"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_draws_draw_number"), table_name="draws")
    op.drop_column("draws", "ingested_at")
    op.drop_column("draws", "source_hash")
    op.drop_column("draws", "source")
    op.drop_column("draws", "ticket_cost_ils")
    op.drop_column("draws", "jackpot")
    op.drop_column("draws", "prize_3")
    op.drop_column("draws", "prize_3_strong")
    op.drop_column("draws", "prize_4")
    op.drop_column("draws", "prize_4_strong")
    op.drop_column("draws", "prize_5")
    op.drop_column("draws", "prize_5_strong")
    op.drop_column("draws", "prize_6")
    op.drop_column("draws", "prize_6_strong")
    op.drop_column("draws", "draw_number")
