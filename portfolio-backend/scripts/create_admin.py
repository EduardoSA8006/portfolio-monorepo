#!/usr/bin/env python
"""
Create the admin user directly in the database.

Usage (interactive password prompt):
    poetry run python scripts/create_admin.py --name "Your Name" --email "you@example.com"

Usage (non-interactive via env var — suitable for CI/CD):
    ADMIN_NAME="..." ADMIN_EMAIL="..." ADMIN_PASSWORD="..." \
    poetry run python scripts/create_admin.py

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


async def create_admin(name: str, email: str, password: str) -> None:
    if not is_strong_password(password):
        print(
            "Error: password too weak.\n"
            "Requirements: min 8 chars, uppercase, lowercase, digit, special character.",
            file=sys.stderr,
        )
        sys.exit(1)

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


def _parse_args() -> tuple[str, str, str]:
    parser = argparse.ArgumentParser(description="Create the portfolio admin user.")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"))
    args = parser.parse_args()

    missing = [k for k, v in {"name": args.name, "email": args.email}.items() if not v]
    if missing:
        parser.error(f"Missing required arguments: {', '.join(missing)}")

    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    if not password:
        print("Error: password is required.", file=sys.stderr)
        sys.exit(1)

    return args.name, args.email, password


if __name__ == "__main__":
    asyncio.run(create_admin(*_parse_args()))
