"""Serviço de persistência de chat com validações de ownership e role."""

from typing import Optional

from labia_chat.db.session import session_scope
from labia_chat.repositories.chat_conversation import ChatConversationRepository
from labia_chat.repositories.chat_message import ChatMessageRepository


class ChatPersistenceService:
    """
    Serviço de persistência de chat com validações de ownership e role.

    Não depende de FastAPI e não levanta HTTPException.
    """

    def __init__(
        self,
        conversation_repository: Optional[ChatConversationRepository] = None,
        message_repository: Optional[ChatMessageRepository] = None,
        session_scope_factory=None,
    ):
        """
        Inicializa o serviço com repositories e factory de sessão.

        Args:
            conversation_repository: Instância de ChatConversationRepository.
            message_repository: Instância de ChatMessageRepository.
            session_scope_factory: Factory que retorna async context manager
                de AsyncSession.
        """
        self.conversation_repository = (
            conversation_repository or ChatConversationRepository()
        )
        self.message_repository = message_repository or ChatMessageRepository()
        self.session_scope_factory = session_scope_factory or session_scope

    async def create_conversation(
        self, user_id: str, title: Optional[str] = None, metadata: Optional[dict] = None
    ):
        """
        Cria uma nova conversa.

        Args:
            user_id: ID do usuário (string UUID).
            title: Título opcional da conversa.
            metadata: Metadados opcionais da conversa.

        Returns:
            ChatConversation criada.
        """
        async with self.session_scope_factory() as session:
            return await self.conversation_repository.create(
                session=session,
                user_id=user_id,
                title=title,
                metadata=metadata,
            )

    async def get_conversation_for_user(
        self, conversation_id: str, user_id: str
    ):
        """
        Obtém uma conversa pelo ID verificando pertencimento ao usuário.

        Args:
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).

        Returns:
            ChatConversation ou None se não encontrada ou não pertencer ao usuário.
        """
        async with self.session_scope_factory() as session:
            return await self.conversation_repository.get_by_id_for_user(
                session=session,
                conversation_id=conversation_id,
                user_id=user_id,
            )

    async def list_conversations_for_user(
        self, user_id: str, include_archived: bool = False
    ):
        """
        Lista conversas de um usuário.

        Args:
            user_id: ID do usuário (string UUID).
            include_archived: Se True, inclui conversas arquivadas.

        Returns:
            Lista de ChatConversation ordenadas por created_at desc.
        """
        async with self.session_scope_factory() as session:
            return await self.conversation_repository.list_for_user(
                session=session,
                user_id=user_id,
                include_archived=include_archived,
            )

    async def archive_conversation_for_user(
        self, conversation_id: str, user_id: str
    ):
        """
        Arquiva uma conversa pertencente ao usuário.

        Args:
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).

        Returns:
            ChatConversation arquivada ou None se não encontrada.
        """
        async with self.session_scope_factory() as session:
            return await self.conversation_repository.archive_for_user(
                session=session,
                conversation_id=conversation_id,
                user_id=user_id,
            )

    async def add_message_for_user(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Adiciona uma mensagem a uma conversa, validando ownership e role.

        Args:
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).
            role: Papel da mensagem (user, assistant, system, tool).
            content: Conteúdo da mensagem.
            model: Nome do modelo usado (opcional).
            metadata: Metadados opcionais da mensagem.

        Returns:
            ChatMessage criada.

        Raises:
            ValueError: Se a conversa não existir, não pertencer ao usuário
                       ou se o role for inválido.
        """
        # Valida role permitida
        allowed_roles = {"user", "assistant", "system", "tool"}
        if role not in allowed_roles:
            roles_str = ", ".join(sorted(allowed_roles))
            raise ValueError(f"Role inválido: {role}. Roles permitidos: {roles_str}")

        async with self.session_scope_factory() as session:
            # Verifica que a conversa existe e pertence ao usuário
            conversation = await self.conversation_repository.get_by_id_for_user(
                session=session,
                conversation_id=conversation_id,
                user_id=user_id,
            )

            if conversation is None:
                raise ValueError(
                    "Conversa não encontrada ou não pertence ao usuário"
                )

            # Calcula o próximo índice de sequência
            sequence_index = await self.message_repository.get_next_sequence_index(
                session=session,
                conversation_id=conversation_id,
            )

            # Cria a mensagem
            return await self.message_repository.create(
                session=session,
                conversation_id=conversation_id,
                role=role,
                content=content,
                sequence_index=sequence_index,
                model=model,
                metadata=metadata,
            )

    async def list_messages_for_user(
        self, conversation_id: str, user_id: str
    ):
        """
        Lista mensagens de uma conversa, validando que a conversa pertence ao usuário.

        Args:
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).

        Returns:
            Lista de ChatMessage ordenadas por sequence_index asc.

        Raises:
            ValueError: Se a conversa não existir ou não pertencer ao usuário.
        """
        async with self.session_scope_factory() as session:
            # Verifica que a conversa existe e pertence ao usuário
            conversation = await self.conversation_repository.get_by_id_for_user(
                session=session,
                conversation_id=conversation_id,
                user_id=user_id,
            )

            if conversation is None:
                raise ValueError(
                    "Conversa não encontrada ou não pertence ao usuário"
                )

            # Lista as mensagens
            return await self.message_repository.list_for_conversation(
                session=session,
                conversation_id=conversation_id,
            )
