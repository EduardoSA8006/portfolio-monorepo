import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import AdminUser


async def get_by_email_hash(email_hash: str, db: AsyncSession) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(AdminUser.email_hash == email_hash)
    )
    return result.scalar_one_or_none()


async def get_by_id(user_id: uuid.UUID, db: AsyncSession) -> AdminUser | None:
    result = await db.execute(
        select(AdminUser).where(AdminUser.id == user_id)
    )
    return result.scalar_one_or_none()
