"""Gerenciamento de sessão assíncrona com SQLAlchemy."""

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


async def get_async_session() -> AsyncSession:
    """
    Dependency para obter sessão assíncrona.

    Pode ser sobrescrita via dependency_overrides nos testes.
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
