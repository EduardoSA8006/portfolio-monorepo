import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Composite index supports the canonical forensic query
    # ("all events of type X in time window Y") without scanning the
    # full table. Order matters: event_type first because most queries
    # filter on it, then created_at for the range scan.
    __table_args__ = (
        Index("ix_auth_events_type_created", "event_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuthEvent id={self.id} type={self.event_type}>"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    # Plain text email, nullable — the email_hash above is the lookup
    # index (HMAC, one-way). The plain text is needed to send
    # transactional mail (verification codes, login notifications) and
    # is auto-backfilled by service.login on the first successful
    # sign-in for rows that predate the d5a1e3f0 migration.
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Fernet-encrypted base32 TOTP secret. Stays NULL until the admin enrolls.
    # Present with totp_enabled=False = enrollment pending (awaiting confirmation).
    # TEXT (not VARCHAR(N)) so a future enrollment scheme that produces a
    # larger blob (e.g. WebAuthn passkey credential) doesn't require a
    # length-bumping migration. In Postgres TEXT and VARCHAR have identical
    # storage and performance characteristics.
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Email-based 2FA. When TOTP is also enabled, TOTP wins (no SMTP
    # round-trip at login time). When only this flag is on, /login
    # issues a 6-digit code via code_store and emails it; the user
    # exchanges it for a session at /login/email-code/verify.
    email_2fa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} active={self.is_active}>"
