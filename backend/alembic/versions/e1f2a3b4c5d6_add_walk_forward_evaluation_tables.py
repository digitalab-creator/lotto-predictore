"""add walk-forward evaluation tables

Revision ID: e1f2a3b4c5d6
Revises: c8e4a1b2d3f0
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "c8e4a1b2d3f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluation_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("strong_algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("params", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("training_cutoff", sa.Date(), nullable=False),
        sa.Column("draw_id", sa.Integer(), nullable=False),
        sa.Column("line_index", sa.Integer(), nullable=False),
        sa.Column("numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("strong_number", sa.Integer(), nullable=False),
        sa.Column("payout_ils", sa.Numeric(14, 2), nullable=False),
        sa.Column("cost_ils", sa.Numeric(8, 2), nullable=False),
        sa.Column("net_ils", sa.Numeric(14, 2), nullable=False),
        sa.Column("hits", sa.Integer(), nullable=False),
        sa.Column("strong_hit", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evaluation_tickets_strategy_id"),
        "evaluation_tickets",
        ["strategy_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_tickets_training_cutoff"),
        "evaluation_tickets",
        ["training_cutoff"],
        unique=False,
    )
    op.create_index(
        op.f("ix_evaluation_tickets_draw_id"),
        "evaluation_tickets",
        ["draw_id"],
        unique=False,
    )

    op.create_table(
        "strategy_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("strong_algorithm_version", sa.String(length=80), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("params", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("roi", sa.Numeric(14, 6), nullable=True),
        sa.Column("mean_payout_per_line", sa.Numeric(14, 4), nullable=True),
        sa.Column("median_payout_per_line", sa.Numeric(14, 4), nullable=True),
        sa.Column("hit_rate_3plus", sa.Numeric(10, 6), nullable=True),
        sa.Column("strong_accuracy", sa.Numeric(10, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(14, 6), nullable=True),
        sa.Column("variance_net", sa.Numeric(18, 6), nullable=True),
        sa.Column("random_percentile", sa.Numeric(8, 4), nullable=True),
        sa.Column("bootstrap_roi_p5", sa.Numeric(14, 6), nullable=True),
        sa.Column("bootstrap_roi_p95", sa.Numeric(14, 6), nullable=True),
        sa.Column("random_baseline_median_roi", sa.Numeric(14, 6), nullable=True),
        sa.Column("random_baseline_p5", sa.Numeric(14, 6), nullable=True),
        sa.Column("random_baseline_p95", sa.Numeric(14, 6), nullable=True),
        sa.Column("independent_draw_count", sa.Integer(), nullable=False),
        sa.Column("has_predictive_edge", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_strategy_summaries_strategy_id"),
        "strategy_summaries",
        ["strategy_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_strategy_summaries_strategy_id"), table_name="strategy_summaries")
    op.drop_table("strategy_summaries")
    op.drop_index(op.f("ix_evaluation_tickets_draw_id"), table_name="evaluation_tickets")
    op.drop_index(op.f("ix_evaluation_tickets_training_cutoff"), table_name="evaluation_tickets")
    op.drop_index(op.f("ix_evaluation_tickets_strategy_id"), table_name="evaluation_tickets")
    op.drop_table("evaluation_tickets")
