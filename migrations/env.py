from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from src.common.config import settings
from src.database.base import Base
from src.database.connection import build_database_url
from src.database.credentials import (
    get_database_credentials,
)

# Importing the models registers every table with Base.metadata.
import src.database.models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Build the migration URL from Secrets Manager."""

    credentials = get_database_credentials()

    database_url = build_database_url(credentials)

    return database_url.render_as_string(
        hide_password=False
    )


def get_connect_args() -> dict[str, object]:
    """Build AsyncPG SSL connection arguments."""

    if settings.postgres_ssl_mode == "disable":
        return {}

    return {
        "ssl": settings.postgres_ssl_mode,
    }


def run_migrations_offline() -> None:
    """Generate SQL without opening a database connection."""

    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
) -> None:
    """Run migrations using a synchronous wrapper."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Connect asynchronously and execute migrations."""

    connectable = create_async_engine(
        get_database_url(),
        poolclass=pool.NullPool,
        connect_args=get_connect_args(),
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(
                do_run_migrations
            )
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Start the asynchronous migration process."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()