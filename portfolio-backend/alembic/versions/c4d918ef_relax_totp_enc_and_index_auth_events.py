"""relax totp_secret_enc to TEXT and index auth_events(event_type, created_at)

Revision ID: c4d918ef
Revises: b2c14e80
Create Date: 2026-04-27

Two unrelated but small schema changes batched together:

1. admin_users.totp_secret_enc: VARCHAR(255) → TEXT.
   Fernet of a base32 TOTP secret fits comfortably in 255, but a future
   enrollment scheme (WebAuthn passkey credential blobs especially) would
   not. Postgres treats TEXT and VARCHAR(N) identically on disk and in
   plans, so the move is free now and avoids a forced ALTER COLUMN later.

2. auth_events: composite index on (event_type, created_at).
   The canonical forensic query is "all `login_failed` events in the last
   N hours" — without this index, every such query is a full table scan
   that grows linearly with traffic. event_type comes first because
   queries always equality-filter on it; created_at second supports the
   range scan tail.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4d918ef"
down_revision: str | None = "b2c14e80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "admin_users",
        "totp_secret_enc",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.create_index(
        "ix_auth_events_type_created",
        "auth_events",
        ["event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_auth_events_type_created", table_name="auth_events")
    op.alter_column(
        "admin_users",
        "totp_secret_enc",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
