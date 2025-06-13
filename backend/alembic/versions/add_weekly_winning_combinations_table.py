"""add weekly winning combinations table

Revision ID: add_weekly_winning_combinations
Revises: 2b81cd7d248b
Create Date: 2024-03-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_weekly_winning_combinations'
down_revision: Union[str, None] = '2b81cd7d248b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('weekly_winning_combinations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('model_id', sa.Integer(), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('strong_model_id', sa.Integer(), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('main_model_params', sa.JSON(), nullable=True),
        sa.Column('strong_model_params', sa.JSON(), nullable=True),
        sa.Column('total_roi', sa.Float(), nullable=False),
        sa.Column('num_prediction_runs', sa.Integer(), nullable=False),
        sa.Column('num_tickets', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.Column('total_prize', sa.Float(), nullable=False),
        sa.Column('week_start_date', sa.Date(), nullable=False),
        sa.Column('week_end_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('weekly_winning_combinations') 