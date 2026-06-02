"""workspace file versions table

Revision ID: 0009_workspace_versions
Revises: 0007_team_content
Create Date: 2026-06-02
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_workspace_versions"
down_revision = "0007_team_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_file_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspace_files.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("version_num", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("size_bytes", sa.BigInteger, default=0),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("author", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_wsv_file_version",
        "workspace_file_versions",
        ["file_id", "version_num"],
    )


def downgrade() -> None:
    op.drop_index("ix_wsv_file_version", table_name="workspace_file_versions")
    op.drop_table("workspace_file_versions")
