"""identity_providers + dept_team_mappings

Revision ID: 0006_identity
Revises: 0005_admin
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_identity"
down_revision: Union[str, None] = "0005_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB()

PROVIDERS = [
    ("ldap", "LDAP / Active Directory"),
    ("wecom", "企业微信"),
    ("saml", "SAML"),
    ("oidc", "OIDC"),
    ("feishu", "飞书"),
]


def _ts():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "identity_providers",
        sa.Column("id", sa.String(24), primary_key=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("config", JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        *_ts(),
    )
    op.create_table(
        "dept_team_mappings",
        sa.Column("id", UUID, server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("provider_id", sa.String(24), sa.ForeignKey("identity_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_basis", sa.String(16), server_default="attribute", nullable=False),
        sa.Column("source_value", sa.String(255), nullable=False),
        sa.Column("dept", sa.String(120), nullable=True),
        sa.Column("default_role", sa.String(16), server_default="member", nullable=False),
        sa.Column("auto_join_team_id", UUID, nullable=True),
        *_ts(),
    )
    op.create_index("ix_dept_team_mappings_provider_id", "dept_team_mappings", ["provider_id"])

    for pid, label in PROVIDERS:
        op.execute(
            sa.text("INSERT INTO identity_providers (id, label, enabled, config) VALUES (:i, :l, false, '{}'::jsonb)")
            .bindparams(i=pid, l=label)
        )


def downgrade() -> None:
    op.drop_table("dept_team_mappings")
    op.drop_table("identity_providers")
