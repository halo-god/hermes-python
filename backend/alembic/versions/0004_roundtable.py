"""conversations.active_agent_ids (roundtable)

Revision ID: 0004_roundtable
Revises: 0003_teams
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_roundtable"
down_revision: Union[str, None] = "0003_teams"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "active_agent_ids",
            postgresql.JSONB(),
            server_default=sa.text("'[\"hermes\"]'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("conversations", "active_agent_ids")
