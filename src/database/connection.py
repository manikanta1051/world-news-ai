from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy import URL, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.common.config import settings
from src.common.logging_config import logger
from src.database.credentials import (
    DatabaseCredentials,
    get_database_credentials,
)
from src.database.exceptions import (
    DatabaseConnectionError,
)


def build_database_url(
    credentials: DatabaseCredentials,
) -> URL:
    """Build a SQLAlchemy AsyncPG connection URL."""

    return URL.create(
        drivername="postgresql+asyncpg",
        username=credentials.username,
        password=(
            credentials.password.get_secret_value()
        ),
        host=credentials.host,
        port=credentials.port,
        database=credentials.database,
    )


def create_database_engine(
    credentials: DatabaseCredentials | None = None,
) -> AsyncEngine:
    """Create the asynchronous PostgreSQL engine."""

    resolved_credentials = (
        credentials
        if credentials is not None
        else get_database_credentials()
    )

    connect_args: dict[str, object] = {}

    if settings.postgres_ssl_mode != "disable":
        connect_args["ssl"] = (
            settings.postgres_ssl_mode
        )

    return create_async_engine(
        build_database_url(
            resolved_credentials
        ),
        echo=settings.postgres_echo,
        pool_size=settings.postgres_pool_size,
        max_overflow=(
            settings.postgres_max_overflow
        ),
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args=connect_args,
    )


@lru_cache
def get_async_engine() -> AsyncEngine:
    """Return one shared asynchronous engine."""

    return create_database_engine()


@lru_cache
def get_session_factory(
) -> async_sessionmaker[AsyncSession]:
    """Return the shared database session factory."""

    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@asynccontextmanager
async def database_session(
) -> AsyncIterator[AsyncSession]:
    """Provide a session with commit and rollback handling."""

    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise


async def check_database_connection(
) -> dict[str, str]:
    """Run a basic PostgreSQL connection test."""

    try:
        async with (
            get_async_engine().connect()
            as connection
        ):
            result = await connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS database_user,
                        version() AS server_version
                    """
                )
            )

            row = result.mappings().one()

    except (
        SQLAlchemyError,
        OSError,
    ) as exc:
        logger.exception(
            "PostgreSQL health check failed"
        )

        raise DatabaseConnectionError(
            str(exc)
        ) from exc

    health_information = {
        "database_name": str(
            row["database_name"]
        ),
        "database_user": str(
            row["database_user"]
        ),
        "server_version": str(
            row["server_version"]
        ),
    }

    logger.info(
        "PostgreSQL connection successful "
        "database=%s user=%s",
        health_information["database_name"],
        health_information["database_user"],
    )

    return health_information


async def close_database_engine() -> None:
    """Close the shared SQLAlchemy connection pool."""

    await get_async_engine().dispose()

    get_async_engine.cache_clear()
    get_session_factory.cache_clear()