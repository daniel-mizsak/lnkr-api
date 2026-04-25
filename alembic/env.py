"""
Alembic migration environment configuration.

@author "Daniel Mizsak" <daniel@mizsak.com>
"""

import asyncio
from logging.config import fileConfig
from typing import TYPE_CHECKING

from sqlalchemy import URL, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from lnkr import models  # noqa: F401
from lnkr.config.database_settings import database_settings
from lnkr.models.base import Base

if TYPE_CHECKING:
    from collections.abc import Iterable

    from alembic.environment import MigrationContext
    from alembic.operations.ops import MigrationScript
    from sqlalchemy.engine import Connection

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option(
    "sqlalchemy.url",
    URL.create(
        drivername="postgresql+psycopg",
        username=database_settings.POSTGRES_USERNAME,
        password=database_settings.POSTGRES_PASSWORD.get_secret_value(),
        host=database_settings.POSTGRES_HOST,
        port=database_settings.POSTGRES_PORT,
        database=database_settings.POSTGRES_DATABASE,
    ).render_as_string(hide_password=False),
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations in 'online' mode."""

    def _process_revision_directives(
        context: MigrationContext,  # noqa: ARG001
        revision: str | Iterable[str | None] | Iterable[str],  # noqa: ARG001
        directives: list[MigrationScript],
    ) -> None:
        """Prevent auto-generation of empty migration scripts.

        https://alembic.sqlalchemy.org/en/latest/cookbook.html#don-t-generate-empty-migrations-with-autogenerate
        """
        assert config.cmd_opts is not None  # noqa: S101
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            assert script.upgrade_ops is not None  # noqa: S101
            if script.upgrade_ops.is_empty():
                directives[:] = []

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        process_revision_directives=_process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
