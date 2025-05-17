"""add training and test params to predictions table

Revision ID: 4f2b1c6d7e89
Revises: 3f1a2b4c5d67
Create Date: 2025-05-17 21:59:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4f2b1c6d7e89'
down_revision = '3f1a2b4c5d67'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('predictions', sa.Column('train_start_date', sa.Date(), nullable=False, server_default=sa.text("'1980-01-01'")))
    op.add_column('predictions', sa.Column('train_end_date', sa.Date(), nullable=False, server_default=sa.text("'1980-01-01'")))
    op.add_column('predictions', sa.Column('num_test_draws', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('predictions', sa.Column('top_n_per_position', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('predictions', 'train_start_date')
    op.drop_column('predictions', 'train_end_date')
    op.drop_column('predictions', 'num_test_draws')
    op.drop_column('predictions', 'top_n_per_position') 