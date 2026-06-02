"""add is_channel to conversations and channel_mode to teams

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("is_channel", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("teams", sa.Column("channel_mode", sa.String(16), nullable=False, server_default="mention"))


def downgrade() -> None:
    op.drop_column("conversations", "is_channel")
    op.drop_column("teams", "channel_mode")
