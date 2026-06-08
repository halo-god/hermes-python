"""add message_id to workspace_files

Revision ID: 0019
Revises: 0018
"""
from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workspace_files",
        sa.Column("message_id", sa.UUID(), sa.ForeignKey("messages.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_workspace_files_message_id", "workspace_files", ["message_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_files_message_id", table_name="workspace_files")
    op.drop_column("workspace_files", "message_id")
