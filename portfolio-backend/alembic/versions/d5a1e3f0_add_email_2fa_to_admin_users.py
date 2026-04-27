"""add email + email_2fa_enabled to admin_users

Revision ID: d5a1e3f0
Revises: c4d918ef
Create Date: 2026-04-27

Two columns gated by the same product change (email-based 2FA):

  * email — plain text RFC 5321 cap (254 chars), nullable. The login
    flow auto-backfills it on first successful sign-in for existing
    rows that pre-date this migration. We can't compute it from
    email_hash (HMAC is one-way by design), so the auto-backfill is
    how migration-time NULLs get filled in without forcing every
    admin into a profile screen.

  * email_2fa_enabled — boolean flag, NOT NULL DEFAULT false. The
    server_default lands so existing rows are explicitly opted-out;
    the default is then dropped so future inserts use the ORM-side
    `default=False` (mirroring how b2c14e80 added totp_enabled).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5a1e3f0"
down_revision: str | None = "c4d918ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column("email", sa.String(length=254), nullable=True),
    )
    op.add_column(
        "admin_users",
        sa.Column(
            "email_2fa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("admin_users", "email_2fa_enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("admin_users", "email_2fa_enabled")
    op.drop_column("admin_users", "email")
