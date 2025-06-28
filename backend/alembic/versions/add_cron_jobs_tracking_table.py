"""add cron jobs tracking table

Revision ID: add_cron_jobs_tracking
Revises: add_weekly_winning_combinations
Create Date: 2025-01-27 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_cron_jobs_tracking'
down_revision: Union[str, None] = 'add_weekly_winning_combinations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cron_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.Enum('running', 'completed', 'failed', name='job_status'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=False, server_default='scheduled'),  # scheduled, manual
        sa.Column('job_metadata', sa.JSON(), nullable=True),  # Additional job-specific data
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for efficient queries
    op.create_index('ix_cron_jobs_job_name', 'cron_jobs', ['job_name'])
    op.create_index('ix_cron_jobs_status', 'cron_jobs', ['status'])
    op.create_index('ix_cron_jobs_started_at', 'cron_jobs', ['started_at'])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_cron_jobs_started_at', table_name='cron_jobs')
    op.drop_index('ix_cron_jobs_status', table_name='cron_jobs')
    op.drop_index('ix_cron_jobs_job_name', table_name='cron_jobs')
    op.drop_table('cron_jobs')
    op.execute('DROP TYPE job_status') 