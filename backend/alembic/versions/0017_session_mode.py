"""add session_mode to conversations

Revision ID: 0017
Revises: 0016_profile_roles
"""
from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("session_mode", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "session_mode")
