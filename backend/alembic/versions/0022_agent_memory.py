"""add agent_memory table

Revision ID: 0022
Revises: 0021
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_memory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("user_profile", sa.Text, nullable=True),
        sa.Column("soul", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_memory_user_id", "agent_memory", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_memory_user_id", table_name="agent_memory")
    op.drop_table("agent_memory")
