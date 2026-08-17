"""Repositório para operações de mensagens ChatMessage."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from labia_chat.models.user import ChatMessage


class ChatMessageRepository:
    """Repositório para operações de mensagens."""

    async def create(
        self,
        session: AsyncSession,
        conversation_id: str,
        role: str,
        content: str,
        sequence_index: int,
        model: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ChatMessage:
        """
        Cria uma nova mensagem.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).
            role: Papel da mensagem (user, assistant, system, tool).
            content: Conteúdo da mensagem.
            sequence_index: Índice de sequência na conversa.
            model: Nome do modelo usado (opcional).
            metadata: Metadados opcionais da mensagem.

        Returns:
            ChatMessage: Instância da mensagem criada.
        """
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_index=sequence_index,
            model=model,
            message_metadata=metadata or {},
        )
        session.add(message)
        return message

    async def list_for_conversation(
        self,
        session: AsyncSession,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        """
        Lista mensagens de uma conversa.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).
            limit: Número máximo de mensagens a retornar.
            offset: Número de mensagens a pular.

        Returns:
            Lista de ChatMessage ordenadas por sequence_index asc.
        """
        stmt = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        stmt = stmt.order_by(ChatMessage.sequence_index.asc())
        stmt = stmt.offset(offset).limit(limit)
        result = await session.scalars(stmt)
        return result.all()

    async def list_recent_for_conversation(
        self, session: AsyncSession, conversation_id: str, limit: int = 50
    ) -> list[ChatMessage]:
        """
        Lista as mensagens mais recentes de uma conversa.

        Seleciona as últimas `limit` mensagens por sequence_index desc e
        retorna em ordem cronológica (sequence_index asc).

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).
            limit: Número máximo de mensagens mais recentes a retornar.

        Returns:
            Lista de ChatMessage ordenadas por sequence_index asc.
        """
        stmt = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
        stmt = stmt.order_by(ChatMessage.sequence_index.desc()).limit(limit)
        result = await session.scalars(stmt)
        return list(reversed(result.all()))

    async def get_next_sequence_index(
        self, session: AsyncSession, conversation_id: str
    ) -> int:
        """
        Obtém o próximo índice de sequência para uma conversa.

        Args:
            session: Sessão async do SQLAlchemy.
            conversation_id: ID da conversa (string UUID).

        Returns:
            0 se não houver mensagens, senão max(sequence_index) + 1.
        """
        stmt = select(func.max(ChatMessage.sequence_index)).where(
            ChatMessage.conversation_id == conversation_id
        )
        result = await session.scalar(stmt)
        return 0 if result is None else result + 1
