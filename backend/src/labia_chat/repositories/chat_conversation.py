"""Repositório para operações de conversas ChatConversation."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from labia_chat.models.user import ChatConversation, utc_now


class ChatConversationRepository:
    """Repositório para operações de conversas."""

    async def create(
        self,
        session: AsyncSession,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ChatConversation:
        """
        Cria uma nova conversa.

        Args:
            session: Sessão async do SQLAlchemy.
            user_id: ID do usuário (string UUID).
            title: Título opcional da conversa.
            metadata: Metadados opcionais da conversa.

        Returns:
            ChatConversation: Instância da conversa criada.
        """
        conversation = ChatConversation(
            user_id=user_id,
            title=title,
            conversation_metadata=metadata or {},
        )
        session.add(conversation)
        return conversation


    async def get_by_id(
        self, session: AsyncSession, conversation_id: str
    ) -> Optional[ChatConversation]:
        """
        Obtém uma conversa pelo ID.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).

        Returns:
            ChatConversation ou None se não encontrada.
        """
        stmt = select(ChatConversation).where(ChatConversation.id == conversation_id)
        return await session.scalar(stmt)

    async def get_by_id_for_user(
        self, session: AsyncSession, conversation_id: str, user_id: str
    ) -> Optional[ChatConversation]:
        """
        Obtém uma conversa pelo ID verificando pertencimento ao usuário.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).

        Returns:
            ChatConversation ou None se não encontrada ou não pertencer ao usuário.
        """
        stmt = select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )
        return await session.scalar(stmt)

    async def list_for_user(
        self, session: AsyncSession, user_id: str, include_archived: bool = False
    ) -> list[ChatConversation]:
        """
        Lista conversas de um usuário.

        Args:
            session: Sessão async do SQLAlchemy.
            user_id: ID do usuário (string UUID).
            include_archived: Se True, inclui conversas arquivadas.

        Returns:
            Lista de ChatConversation ordenadas por created_at desc.
        """
        stmt = select(ChatConversation).where(ChatConversation.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(ChatConversation.archived_at.is_(None))
        stmt = stmt.order_by(ChatConversation.created_at.desc())
        result = await session.scalars(stmt)
        return result.all()

    async def archive_for_user(
        self, session: AsyncSession, conversation_id: str, user_id: str
    ) -> Optional[ChatConversation]:
        """
        Arquiva uma conversa pertencente ao usuário.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).

        Returns:
            ChatConversation arquivada ou None se não encontrada.
        """
        stmt = select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )
        conversation = await session.scalar(stmt)
        if conversation is not None:
            conversation.archived_at = utc_now()
        return conversation

