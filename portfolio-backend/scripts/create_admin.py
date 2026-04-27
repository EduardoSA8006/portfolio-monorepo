#!/usr/bin/env python
"""
Create or reset the admin user directly in the database.

Create (interactive password prompt):
    poetry run python scripts/create_admin.py --name "Your Name" --email "you@example.com"

Create (non-interactive via env var — suitable for CI/CD):
    ADMIN_NAME="..." ADMIN_EMAIL="..." ADMIN_PASSWORD="..." \
    poetry run python scripts/create_admin.py

Reset password + clear TOTP for an existing admin (recovery scenario):
    poetry run python scripts/create_admin.py --reset --email "you@example.com"

The --password CLI argument is intentionally absent: command-line passwords
appear in shell history, ps aux output, and system logs.
"""
import argparse
import asyncio
import getpass
import os
import sys

# Ensure project root is on the path when running directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.features.auth.models import AdminUser
from app.shared.security import hash_email, hash_password, is_strong_password


def _check_password_or_exit(password: str) -> None:
    if not is_strong_password(password):
        print(
            "Error: password too weak.\n"
            "Requirements: min 8 chars, uppercase, lowercase, digit, special character.",
            file=sys.stderr,
        )
        sys.exit(1)


async def create_admin(name: str, email: str, password: str) -> None:
    _check_password_or_exit(password)
    email_hash = hash_email(email)

    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(AdminUser).where(AdminUser.email_hash == email_hash)
        )
        if existing.scalar_one_or_none():
            print("Error: an admin with this email already exists.", file=sys.stderr)
            sys.exit(1)

        user = AdminUser(
            name=name,
            email_hash=email_hash,
            password_hash=hash_password(password),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    print(f"Admin '{name}' created successfully (id={user.id}).")


async def reset_admin(email: str, password: str) -> None:
    """Recovery path: re-set the password and clear TOTP enrollment.

    Used when the admin loses both their password and their authenticator
    device. Requires direct DB access (so it cannot be triggered remotely)
    and is documented in docs/runbook-admin-recovery.md.
    """
    _check_password_or_exit(password)
    email_hash = hash_email(email)

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AdminUser).where(AdminUser.email_hash == email_hash)
        )
        user = result.scalar_one_or_none()
        if user is None:
            print(f"Error: no admin found with email {email}.", file=sys.stderr)
            sys.exit(1)

        user.password_hash = hash_password(password)
        # Wipe TOTP enrollment in lock-step so the recovered admin is
        # forced to re-enroll. Leaving totp_enabled=True with a stale
        # secret would lock them out again at next login.
        user.totp_secret_enc = None
        user.totp_enabled = False
        await db.commit()

    print(
        f"Admin {email} reset successfully (id={user.id}). "
        "TOTP cleared — re-enroll on first login."
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create or reset the portfolio admin user.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset an existing admin's password and clear TOTP (recovery).",
    )
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    args = parser.parse_args()

    if args.reset:
        if not args.email:
            parser.error("--reset requires --email (or ADMIN_EMAIL).")
    else:
        missing = [k for k, v in {"name": args.name, "email": args.email}.items() if not v]
        if missing:
            parser.error(f"Missing required arguments: {', '.join(missing)}")

    args.password = os.getenv("ADMIN_PASSWORD") or getpass.getpass(
        "New password: " if args.reset else "Admin password: "
    )
    if not args.password:
        print("Error: password is required.", file=sys.stderr)
        sys.exit(1)

    return args


async def _main() -> None:
    args = _parse_args()
    if args.reset:
        await reset_admin(args.email, args.password)
    else:
        await create_admin(args.name, args.email, args.password)


if __name__ == "__main__":
    asyncio.run(_main())
