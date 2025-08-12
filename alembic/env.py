# alembic/env.py
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Load .env early so env vars are available (optional but helpful)
try:
    from dotenv import load_dotenv  # python-dotenv
    load_dotenv()
except Exception:
    # it's fine if dotenv isn't installed; env vars may come from elsewhere
    pass

# Import your app metadata (Base) and settings
from app.database import Base
from app.dependencies import get_settings

# Alembic Config object, provides access to .ini values
config = context.config


# Configure Python logging from alembic.ini if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate'
target_metadata = Base.metadata


def _get_sync_database_url() -> str:
    # 1) Prefer an override if present (helps local dev)
    override = os.getenv("ALEMBIC_DATABASE_URL")
    if override:
        return override

    settings = get_settings()
    url = settings.database_url

    # normalize async URLs to sync
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("sqlite+aiosqlite:///"):
        return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
    return url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    Uses a URL and does not require a live DBAPI connection.
    """
    sync_url = _get_sync_database_url()
    # Inject URL into alembic config so script env sees it
    config.set_main_option("sqlalchemy.url", sync_url)

    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # helpful for detecting column type changes
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    Creates an Engine and associates a live connection with the context.
    """
    sync_url = _get_sync_database_url()
    config.set_main_option("sqlalchemy.url", sync_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
