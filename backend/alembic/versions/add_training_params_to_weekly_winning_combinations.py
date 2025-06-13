"""add training params to weekly winning combinations

Revision ID: add_training_params
Revises: add_weekly_winning_combinations
Create Date: 2024-03-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_training_params'
down_revision: Union[str, None] = 'add_weekly_winning_combinations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    # Add training parameters to main_model_params JSON while preserving existing ones
    op.execute("""
        UPDATE weekly_winning_combinations
        SET main_model_params = CASE
            WHEN main_model_params IS NULL THEN '{"training_params": {"train_start_date": null, "train_end_date": null, "test_count": 12}}'::jsonb
            ELSE main_model_params::jsonb || '{"training_params": {"train_start_date": null, "train_end_date": null, "test_count": 12}}'::jsonb
        END
        WHERE main_model_params IS NULL OR NOT main_model_params::jsonb ? 'training_params'
    """)

def downgrade() -> None:
    """Downgrade schema."""
    # Remove only the training parameters from main_model_params JSON
    op.execute("""
        UPDATE weekly_winning_combinations
        SET main_model_params = main_model_params::jsonb - 'training_params'
        WHERE main_model_params IS NOT NULL
    """) 