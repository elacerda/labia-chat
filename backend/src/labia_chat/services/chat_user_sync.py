"""Serviço para sincronização de usuário ChatUser."""

from typing import AsyncContextManager, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from labia_chat.core.errors import ExternalServiceError
from labia_chat.db.session import session_scope
from labia_chat.models.user import ChatUser
from labia_chat.repositories.chat_user import ChatUserRepository
from labia_chat.schemas.user import AuthenticatedUser


class SessionScopeFactory(Protocol):
    """Protocolo para factory de session scope."""

    def __call__(self) -> AsyncContextManager[AsyncSession]: ...


class ChatUserSyncService:
    """Serviço para sincronizar usuário autenticado na tabela chat_users."""

    def __init__(
        self,
        repository: ChatUserRepository | None = None,
        session_scope_factory: SessionScopeFactory | None = None,
    ):
        """
        Inicializa o serviço de sincronização.

        Args:
            repository: Instância de ChatUserRepository. Se não fornecida,
            cria uma nova.
            session_scope_factory: Factory que retorna um async context manager
            de AsyncSession. Se não fornecida, usa session_scope padrão.
        """
        self._repository = repository or ChatUserRepository()
        self._session_scope_factory = session_scope_factory or session_scope

    async def sync(self, user: AuthenticatedUser) -> ChatUser:
        """
        Sincroniza usuário na tabela chat_users.

        Args:
            user: AuthenticatedUser com dados do ADSS.

        Returns:
            ChatUser: Instância do usuário sincronizado (criado ou atualizado).

        Raises:
            ExternalServiceError: Se houver falha ao acessar o banco de dados.
        """
        try:
            async with self._session_scope_factory() as session:
                return await self._repository.upsert(session, user)
        except ExternalServiceError:
            raise
        except Exception as exc:
            raise ExternalServiceError(f"Failed to sync user: {exc}") from exc
