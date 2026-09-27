"""add ticket packs, real batches, pack deliveries

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_packs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("target_draw_number", sa.Integer(), nullable=True),
        sa.Column("target_draw_date", sa.Date(), nullable=True),
        sa.Column("lines", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("planned_cost_ils", sa.Numeric(10, 2), nullable=False),
        sa.Column("strategy_id", sa.String(length=160), nullable=True),
        sa.Column("main_algorithm", sa.String(length=80), nullable=False),
        sa.Column("strong_algorithm", sa.String(length=80), nullable=False),
        sa.Column("training_cutoff", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="pending_purchase",
        ),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("no_edge_label", sa.String(length=120), nullable=True),
        sa.Column("strategy_meta", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_ticket_packs_target_draw_number"),
        "ticket_packs",
        ["target_draw_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ticket_packs_status"),
        "ticket_packs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "real_ticket_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_pack_id", sa.Integer(), nullable=False),
        sa.Column("draw_id", sa.Integer(), nullable=True),
        sa.Column("investment_ils", sa.Numeric(10, 2), nullable=False),
        sa.Column("payout_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("net_ils", sa.Numeric(14, 2), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lines_snapshot", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["ticket_pack_id"], ["ticket_packs.id"]),
        sa.ForeignKeyConstraint(["draw_id"], ["draws.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_pack_id"),
    )

    op.create_table(
        "pack_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_pack_id", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ticket_pack_id"], ["ticket_packs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pack_deliveries_ticket_pack_id"),
        "pack_deliveries",
        ["ticket_pack_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pack_deliveries_ticket_pack_id"), table_name="pack_deliveries")
    op.drop_table("pack_deliveries")
    op.drop_table("real_ticket_batches")
    op.drop_index(op.f("ix_ticket_packs_status"), table_name="ticket_packs")
    op.drop_index(op.f("ix_ticket_packs_target_draw_number"), table_name="ticket_packs")
    op.drop_table("ticket_packs")
