"""
AutoForge Database Engine — SQLAlchemy async engine + session factory.

Provides:
- Async engine for PostgreSQL via asyncpg
- Async session factory
- Base declarative model
- Graceful fallback to SQLite for local dev / testing
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import settings
from logging_config import get_logger

log = get_logger("db.engine")


def _build_url() -> str:
    """Convert DATABASE_URL to async driver URL."""
    url = settings.DATABASE_URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


_engine = None
_session_factory = None


def get_engine():
    """Lazy-create the async engine."""
    global _engine
    if _engine is None:
        db_url = _build_url()
        _engine = create_async_engine(
            db_url,
            echo=settings.APP_DEBUG and not settings.DEMO_MODE,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
        )
        log.info("db_engine_created", url=db_url.split("@")[-1] if "@" in db_url else db_url)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazy-create the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db():
    """Create all tables (dev/test convenience — use Alembic in production)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    log.info("db_tables_created")


async def close_db():
    """Dispose of the engine pool."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        log.info("db_engine_disposed")
