"""add composite index on conversations(owner_id, updated_at)

Revision ID: 0026
Revises: 0025
Create Date: 2026-06-12
"""
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_conv_owner_updated",
        "conversations",
        ["owner_id", "updated_at"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_conv_owner_updated", table_name="conversations")
