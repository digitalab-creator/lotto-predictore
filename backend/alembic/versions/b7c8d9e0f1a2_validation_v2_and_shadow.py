"""validation v2, shadow commitments, coverage cache

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "validation_experiments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("regime_start", sa.Date(), nullable=False),
        sa.Column("select_start_date", sa.Date(), nullable=False),
        sa.Column("holdout_start_date", sa.Date(), nullable=False),
        sa.Column("holdout_end_date", sa.Date(), nullable=False),
        sa.Column("draw_count", sa.Integer(), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("refusal_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "validation_locks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("main_algorithm", sa.String(length=80), nullable=False),
        sa.Column("strong_algorithm", sa.String(length=80), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("primary_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("first_half_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("second_half_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("promoted", sa.Boolean(), nullable=False),
        sa.Column("candidate_scores", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("locked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["validation_experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
    )
    op.create_table(
        "validation_holdout_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("seal", sa.Integer(), nullable=False),
        sa.Column("verdict", sa.String(length=32), nullable=False),
        sa.Column("report", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["validation_experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id"),
        sa.UniqueConstraint("seal"),
    )
    op.create_table(
        "validation_steps",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("stage", sa.String(length=16), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=False),
        sa.Column("draw_id", sa.Integer(), nullable=True),
        sa.Column("draw_date", sa.Date(), nullable=False),
        sa.Column("lines", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("ticket_wins", sa.Integer(), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("tier_counts", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("mean_main_hits", sa.Numeric(8, 4), nullable=False),
        sa.Column("payout_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("cost_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("random_ticket_rate", sa.Numeric(12, 8), nullable=True),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"]),
        sa.ForeignKeyConstraint(["experiment_id"], ["validation_experiments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("experiment_id", "stage", "strategy_id", "draw_date", name="uq_validation_step"),
    )
    op.create_index("ix_validation_steps_experiment_id", "validation_steps", ["experiment_id"])
    op.create_table(
        "shadow_commitments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("lines", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("lines_hash", sa.String(length=64), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("git_sha", sa.String(length=40), nullable=False),
        sa.Column("main_algorithm", sa.String(length=80), nullable=False),
        sa.Column("strong_algorithm", sa.String(length=80), nullable=False),
        sa.Column("training_cutoff", sa.Date(), nullable=False),
        sa.Column("target_draw_number", sa.Integer(), nullable=True),
        sa.Column("ticket_pack_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["ticket_pack_id"], ["ticket_packs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_commitments_target_draw_number", "shadow_commitments", ["target_draw_number"])
    op.create_table(
        "shadow_outcomes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("commitment_id", sa.Integer(), nullable=False),
        sa.Column("draw_id", sa.Integer(), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("winning_lines", sa.Integer(), nullable=False),
        sa.Column("payout_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("cost_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("detail", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["commitment_id"], ["shadow_commitments.id"]),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("commitment_id"),
    )
    op.create_table(
        "coverage_portfolios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("regime_start", sa.Date(), nullable=False),
        sa.Column("lines", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("p_any", sa.Numeric(12, 8), nullable=False),
        sa.Column("report", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coverage_portfolios_regime_start", "coverage_portfolios", ["regime_start"])
    op.execute(
        """
        CREATE OR REPLACE FUNCTION shadow_commitments_append_only()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'shadow_commitments are append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER shadow_commitments_no_change
        BEFORE UPDATE OR DELETE ON shadow_commitments
        FOR EACH ROW EXECUTE FUNCTION shadow_commitments_append_only();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS shadow_commitments_no_change ON shadow_commitments")
    op.execute("DROP FUNCTION IF EXISTS shadow_commitments_append_only()")
    op.drop_index("ix_coverage_portfolios_regime_start", table_name="coverage_portfolios")
    op.drop_table("coverage_portfolios")
    op.drop_table("shadow_outcomes")
    op.drop_index("ix_shadow_commitments_target_draw_number", table_name="shadow_commitments")
    op.drop_table("shadow_commitments")
    op.drop_index("ix_validation_steps_experiment_id", table_name="validation_steps")
    op.drop_table("validation_steps")
    op.drop_table("validation_holdout_results")
    op.drop_table("validation_locks")
    op.drop_table("validation_experiments")
