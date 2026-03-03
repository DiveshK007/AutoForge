"""
AutoForge — Alembic environment configuration.

Reads DATABASE_URL from settings and runs migrations against the real DB.
Supports both online (connected) and offline (SQL-generation) modes.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, create_engine

# ─── Import AutoForge models so autogenerate can detect them ───
import sys
import os

# Ensure backend/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.engine import _build_url, Base  # noqa: E402
from db import tables  # noqa: E402, F401  — registers all ORM models
from config import settings  # noqa: E402

# ─── Alembic Config ───
config = context.config

# Override sqlalchemy.url with the real DATABASE_URL
db_url = _build_url(settings.DATABASE_URL).replace("+asyncpg", "")  # alembic needs sync driver
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to DB and applies."""
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
