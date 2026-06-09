"""add user preferences column

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021"
down_revision = "0020_conversation_channel_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("preferences", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferences")
