"""add bot_settings table

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa

revision = 'h2i3j4k5l6m7'
down_revision = 'g1h2i3j4k5l6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'bot_settings',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('description', sa.String(256), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('bot_settings')
