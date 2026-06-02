"""teams, team_members, projects, project_tasks

Revision ID: 0003_teams
Revises: 0002_conversations
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_teams"
down_revision: Union[str, None] = "0002_conversations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def _ts_cols():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("handle", sa.String(64), nullable=True),
        sa.Column("tagline", sa.String(200), nullable=True),
        sa.Column("color", sa.String(16), server_default="#b8852a", nullable=True),
        sa.Column("plan", sa.String(24), server_default="team", nullable=False),
        sa.Column("join_mode", sa.String(24), server_default="invite", nullable=False),
        sa.Column("policy", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts_cols(),
    )
    op.create_index("ix_teams_handle", "teams", ["handle"], unique=True)

    op.create_table(
        "team_members",
        sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(16), server_default="member", nullable=False),
        sa.Column("status", sa.String(16), server_default="offline", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        *_ts_cols(),
    )

    op.create_table(
        "projects",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("handle", sa.String(64), nullable=True),
        sa.Column("color", sa.String(16), server_default="#b8852a", nullable=True),
        sa.Column("icon", sa.String(40), server_default="sparkle", nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("sections", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("pinned_agents", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("visibility", sa.String(16), server_default="team", nullable=False),
        sa.Column("deadline", sa.Date(), nullable=True),
        *_ts_cols(),
    )
    op.create_index("ix_projects_team_id", "projects", ["team_id"])

    op.create_table(
        "project_tasks",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("status", sa.String(16), server_default="todo", nullable=False),
        sa.Column("owner_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=True),
        sa.Column("order_idx", sa.Integer(), server_default="0", nullable=False),
        *_ts_cols(),
    )
    op.create_index("ix_project_tasks_project_id", "project_tasks", ["project_id"])


def downgrade() -> None:
    op.drop_table("project_tasks")
    op.drop_table("projects")
    op.drop_table("team_members")
    op.drop_table("teams")
