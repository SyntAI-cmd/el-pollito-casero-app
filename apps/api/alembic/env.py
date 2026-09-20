"""
Alembic sobre el engine async. La URL sale de la configuración de la app (DATABASE_URL), así
migraciones y servidor apuntan siempre a la misma base.
"""

import asyncio
from typing import Any

from sqlalchemy import JSON, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import app.core.modelos  # noqa: F401  (registra todas las tablas)
from alembic import context
from app.core.config import get_settings
from app.core.db import Base
from app.core.tipos import FechaHora

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def render_item(tipo: str, obj: Any, autogen_context: Any) -> str | bool:
    """Los tipos propios se escriben en la migración como SQLAlchemy puro y portable."""
    if tipo == "type":
        if isinstance(obj, FechaHora):
            return "sa.DateTime(timezone=True)"
        if isinstance(obj, JSON):
            autogen_context.imports.add("from sqlalchemy.dialects import postgresql")
            return 'sa.JSON().with_variant(postgresql.JSONB(), "postgresql")'
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
