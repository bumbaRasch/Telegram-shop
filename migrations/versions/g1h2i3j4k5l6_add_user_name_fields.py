"""add username first_name last_name to users

Revision ID: g1h2i3j4k5l6
Revises: d4e5f6a7b8c9
Create Date: 2026-03-27

"""
from alembic import op
import sqlalchemy as sa

revision = 'g1h2i3j4k5l6'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('username', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('first_name', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(64), nullable=True))
    op.create_index('ix_users_username', 'users', ['username'])


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'username')
