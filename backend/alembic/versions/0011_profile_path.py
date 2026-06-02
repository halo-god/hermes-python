"""add path column to profiles

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "path")
