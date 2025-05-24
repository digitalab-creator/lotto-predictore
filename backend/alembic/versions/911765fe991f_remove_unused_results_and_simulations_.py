"""remove unused results and simulations tables

Revision ID: 911765fe991f
Revises: 4f2b1c6d7e89
Create Date: 2025-05-18 19:18:15.144919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '911765fe991f'
down_revision: Union[str, None] = '4f2b1c6d7e89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('ix_results_id'), table_name='results')
    op.drop_table('results')
    op.drop_index(op.f('ix_simulations_id'), table_name='simulations')
    op.drop_table('simulations')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table('simulations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.String(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('sim_type', sa.String(), nullable=True),
        sa.Column('rows_generated', sa.Integer(), nullable=False),
        sa.Column('avg_hits', sa.Float(), nullable=True),
        sa.Column('total_prize', sa.Float(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_simulations_id'), 'simulations', ['id'], unique=False)
    op.create_table('results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('combination_id', sa.Integer(), nullable=False),
        sa.Column('draw_id', sa.Integer(), nullable=False),
        sa.Column('hits', sa.Integer(), nullable=False),
        sa.Column('strong_hit', sa.Boolean(), nullable=False),
        sa.Column('prize', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['combination_id'], ['generated_combinations.id'], ),
        sa.ForeignKeyConstraint(['draw_id'], ['draws.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_results_id'), 'results', ['id'], unique=False)
