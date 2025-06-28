"""Merge heads

Revision ID: 15920a4b9132
Revises: add_cron_jobs_tracking, add_training_params
Create Date: 2025-06-28 14:25:50.765184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15920a4b9132'
down_revision: Union[str, None] = ('add_cron_jobs_tracking', 'add_training_params')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
