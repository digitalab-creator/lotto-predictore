"""move top_n_per_position to main_model_params json

Revision ID: f01ee062df86
Revises: 911765fe991f
Create Date: 2025-05-18 19:46:16.352865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f01ee062df86'
down_revision: Union[str, None] = '911765fe991f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('predictions', 'top_n_per_position')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('predictions', sa.Column('top_n_per_position', sa.Integer(), nullable=True))
