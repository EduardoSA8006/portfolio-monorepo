"""create_admin_users_table

Revision ID: 69e9b063
Revises:
Create Date: 2026-04-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "69e9b063"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("email_hash", sa.String(64), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Single unique index enforces the column-level unique=True from the ORM model.
    # No separate UniqueConstraint — it would create a duplicate unique index in PG.
    op.create_index("ix_admin_users_email_hash", "admin_users", ["email_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_admin_users_email_hash", table_name="admin_users")
    op.drop_table("admin_users")
