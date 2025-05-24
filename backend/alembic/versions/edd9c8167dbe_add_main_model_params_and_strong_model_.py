"""add main_model_params and strong_model_params to predictions

Revision ID: edd9c8167dbe
Revises: f01ee062df86
Create Date: 2025-05-18 19:51:07.704531

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'edd9c8167dbe'
down_revision: Union[str, None] = 'f01ee062df86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('predictions', sa.Column('main_model_params', sa.JSON(), nullable=True))
    op.add_column('predictions', sa.Column('strong_model_params', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('predictions', 'main_model_params')
    op.drop_column('predictions', 'strong_model_params')
