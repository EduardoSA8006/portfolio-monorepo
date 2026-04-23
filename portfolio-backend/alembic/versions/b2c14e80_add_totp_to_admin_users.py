"""add totp columns to admin_users

Revision ID: b2c14e80
Revises: 3a7f21bc
Create Date: 2026-04-23

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c14e80"
down_revision: str | None = "3a7f21bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("totp_secret_enc", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Drop server_default so future inserts are driven by the ORM default.
    op.alter_column("admin_users", "totp_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("admin_users", "totp_enabled")
    op.drop_column("admin_users", "totp_secret_enc")
