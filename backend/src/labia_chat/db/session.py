"""Gerenciamento de sessão assíncrona com SQLAlchemy."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from labia_chat.core.config import settings

# Variáveis para armazenar engine e sessionmaker criados lazy
_engine = None
_sessionmaker = None


def get_engine():
    """Obter engine assíncrono (criação lazy)."""
    global _engine
    if _engine is None:
        if not settings.database_url:
            msg = (
                "DATABASE_URL não configurada. Configure a variável de ambiente "
                "DATABASE_URL no arquivo .env ou no ambiente do sistema. "
                "Exemplo: DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname"
            )
            raise RuntimeError(msg)
        _engine = create_async_engine(
            settings.database_url,
            echo=False,  # Definir True para debug SQL
            pool_pre_ping=True,  # Verificar conexões antes de usar
            pool_size=10,
            max_overflow=20,
        )
    return _engine


def get_sessionmaker():
    """Obter async_sessionmaker (criação lazy)."""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _sessionmaker


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """
    Context manager para gerenciar sessão com transação.

    Abre uma sessão, faz commit em caso de sucesso, rollback em caso de erro
    e relança a exceção. O async with cuida do fechamento da sessão.

    Exemplo de uso:
        async with session_scope() as session:
            await session.execute(query)

    Yields:
        AsyncSession: Sessão assíncrona com gerenciamento de transação.

    Raises:
        Exception: Qualquer exceção ocorrida durante a operação.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """
    Dependency para obter sessão assíncrona.

    Pode ser sobrescrita via dependency_overrides nos testes.

    Args:
        session_factory: Factory que retorna um async context manager de AsyncSession.

    Yields:
        AsyncSession: Sessão assíncrona.
    """
    async with session_scope() as session:
        yield session
