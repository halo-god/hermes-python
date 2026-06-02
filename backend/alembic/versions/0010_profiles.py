"""profiles table with default seed data

Revision ID: 0010_profiles
Revises: 0009_workspace_versions
Create Date: 2026-06-02
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_profiles"
down_revision = "0009_workspace_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("handle", sa.String(64), nullable=False, unique=True),
        sa.Column("scope", sa.String(16), nullable=False, server_default="personal"),
        sa.Column("color", sa.String(16), nullable=False, server_default="#b8852a"),
        sa.Column("icon", sa.String(40), nullable=False, server_default="brand"),
        sa.Column("desc", sa.Text, nullable=True),
        sa.Column("default_agent_id", sa.String(64), nullable=False, server_default="hermes"),
        sa.Column("default_model", sa.String(64), nullable=False, server_default="hermes-4"),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Seed default profiles -- use "desc" (quoted) in raw SQL since desc is a PG reserved word
    op.execute(
        """
        INSERT INTO profiles (id, name, handle, scope, color, icon, "desc", default_agent_id, default_model, team_id, is_active)
        VALUES
          (gen_random_uuid(), '主信使', 'hermes-main', 'personal', '#b8852a', 'brand',
           '默认 Hermes Agent，连接本机 ACP 会话', 'hermes', 'hermes-4', NULL, true),
          (gen_random_uuid(), '团队共享', 'hermes-team', 'team', '#3a6da1', 'users',
           '团队共享记忆的 Hermes Profile', 'hermes', 'hermes-4', NULL, true)
        ON CONFLICT (handle) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_table("profiles")
