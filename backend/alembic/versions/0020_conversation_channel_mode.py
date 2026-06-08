"""add channel_mode to conversations

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_conversation_channel_mode"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("channel_mode", sa.String(16), nullable=False, server_default="mention"),
    )


def downgrade() -> None:
    op.drop_column("conversations", "channel_mode")
