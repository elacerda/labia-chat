"""Configuração do Alembic para migrations do banco de dados."""

from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
import asyncio

from alembic import context

from labia_chat.core.config import settings
from labia_chat.db.base import Base

# Importar modelos para que o Alembic os conheça via Base.metadata
# Isso garante que novas tabelas sejam detectadas por autogenerate
from labia_chat.models import ChatUser  # noqa: F401

# Configuração do Alembic
config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model's MetaData object para 'autogenerate' suportar
target_metadata = Base.metadata

# Outras variáveis de configuração do Alembic
def get_url():
    """Obter URL do banco de dados do Settings."""
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required to run Alembic migrations. Configure DATABASE_URL in .env file.")
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    connectable = create_async_engine(
        get_url(),
        poolclass=NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()