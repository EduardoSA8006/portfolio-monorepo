from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    # SQL echo is opt-in via DB_ECHO=true. Enabling it emits every query —
    # including parameter values like email_hash — into stdout/loggers.
    # Leaving it off by default avoids training the team to tolerate sensitive
    # data in logs even in development.
    echo=settings.DB_ECHO,
    # Pool sizing: business sessions (login/MFA) and audit-event sessions
    # share this engine — `audit.record_event` opens an isolated
    # AsyncSessionLocal() per event. SQLAlchemy's default 5+10 is too
    # tight under any sustained load: a captcha-provider slowdown can
    # make audit writes pile up behind login traffic on pool checkout.
    # Postgres max_connections=100 by default; 30 connections per
    # worker × 4 workers still leaves headroom for psql / migrations.
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    # Recycle idle connections hourly so a Postgres-side idle timeout
    # (or a pgbouncer/proxy drop) never surfaces as a stale connection.
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
