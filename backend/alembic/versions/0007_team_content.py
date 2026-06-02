"""team/project content: conversation linkage, shared agents, knowledge, members, docs

Revision ID: 0007_team_content
Revises: 0006_identity
Create Date: 2026-05-31
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_team_content"
down_revision: Union[str, None] = "0006_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    # link conversations to a team / project
    op.add_column("conversations", sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True))
    op.add_column("conversations", sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True))
    op.create_index("ix_conversations_team_id", "conversations", ["team_id"])
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])

    # team shared agents + project member ids
    op.add_column("teams", sa.Column("shared_agents", JSONB, server_default=sa.text('\'["hermes"]\'::jsonb'), nullable=False))
    op.add_column("projects", sa.Column("member_ids", JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False))

    op.create_table(
        "team_knowledge",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("team_id", UUID, sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), server_default="doc", nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("uploaded_by", UUID, nullable=True),
        sa.Column("uploaded_by_name", sa.String(120), nullable=True),
        *_ts(),
    )
    op.create_index("ix_team_knowledge_team_id", "team_knowledge", ["team_id"])

    op.create_table(
        "project_docs",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_id", UUID, sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(16), server_default="doc", nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_by_name", sa.String(120), nullable=True),
        *_ts(),
    )
    op.create_index("ix_project_docs_project_id", "project_docs", ["project_id"])


def downgrade() -> None:
    op.drop_table("project_docs")
    op.drop_table("team_knowledge")
    op.drop_column("projects", "member_ids")
    op.drop_column("teams", "shared_agents")
    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_index("ix_conversations_team_id", table_name="conversations")
    op.drop_column("conversations", "project_id")
    op.drop_column("conversations", "team_id")
