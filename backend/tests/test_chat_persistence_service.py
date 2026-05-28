"""Testes unitários para o serviço ChatPersistenceService."""

import uuid
from unittest.mock import MagicMock

import pytest

from labia_chat.repositories.chat_conversation import ChatConversationRepository
from labia_chat.repositories.chat_message import ChatMessageRepository
from labia_chat.services.chat_persistence import ChatPersistenceService


class FakeAsyncSession:
    """Fake de AsyncSession para testes."""

    def __init__(self):
        self.added_objects = []
        self.scalars_results = []
        self.scalar_results = []
        self.queries = []

    def add(self, obj):
        """Simula add."""
        self.added_objects.append(obj)

    async def scalars(self, stmt):
        """Simula scalars - retorna o próprio stmt com all() como método sync."""
        self.queries.append(stmt)
        result = MagicMock()
        result.all = lambda: self.scalars_results
        return result

    async def scalar(self, stmt):
        """Simula scalar."""
        self.queries.append(stmt)
        if self.scalar_results:
            return self.scalar_results.pop(0)
        return None


class FakeConversationRepository:
    """Fake de ChatConversationRepository para testes."""

    def __init__(self):
        self.create_calls = []
        self.get_by_id_for_user_calls = []
        self.list_for_user_calls = []
        self.archive_for_user_calls = []

    async def create(self, session, user_id, title=None, metadata=None):
        """Simula create."""
        self.create_calls.append((session, user_id, title, metadata))
        fake_conv = MagicMock()
        fake_conv.id = str(uuid.uuid4())
        fake_conv.user_id = user_id
        fake_conv.title = title
        fake_conv.conversation_metadata = metadata or {}
        return fake_conv

    async def get_by_id_for_user(self, session, conversation_id, user_id):
        """Simula get_by_id_for_user."""
        self.get_by_id_for_user_calls.append((session, conversation_id, user_id))
        # Retorna None se user_id for "wrong_user" para testar validação
        if user_id == "wrong_user":
            return None
        fake_conv = MagicMock()
        fake_conv.id = conversation_id
        fake_conv.user_id = user_id
        return fake_conv

    async def list_for_user(
        self, session, user_id, include_archived=False, limit=20, offset=0
    ):
        """Simula list_for_user."""
        self.list_for_user_calls.append(
            (session, user_id, include_archived, limit, offset)
        )
        return []

    async def archive_for_user(self, session, conversation_id, user_id):
        """Simula archive_for_user."""
        self.archive_for_user_calls.append((session, conversation_id, user_id))
        fake_conv = MagicMock()
        fake_conv.id = conversation_id
        fake_conv.user_id = user_id
        fake_conv.archived_at = None
        return fake_conv


class FakeMessageRepository:
    """Fake de ChatMessageRepository para testes."""

    def __init__(self):
        self.create_calls = []
        self.list_for_conversation_calls = []
        self.get_next_sequence_index_calls = []

    async def create(
        self,
        session,
        conversation_id,
        role,
        content,
        sequence_index,
        model=None,
        metadata=None,
    ):
        """Simula create."""
        self.create_calls.append(
            (session, conversation_id, role, content, sequence_index, model, metadata)
        )
        fake_msg = MagicMock()
        fake_msg.id = str(uuid.uuid4())
        fake_msg.conversation_id = conversation_id
        fake_msg.role = role
        fake_msg.content = content
        fake_msg.sequence_index = sequence_index
        fake_msg.model = model
        fake_msg.message_metadata = metadata or {}
        return fake_msg

    async def list_for_conversation(self, session, conversation_id, limit=50, offset=0):
        """Simula list_for_conversation."""
        self.list_for_conversation_calls.append(
            (session, conversation_id, limit, offset)
        )
        return []

    async def get_next_sequence_index(self, session, conversation_id):
        """Simula get_next_sequence_index."""
        self.get_next_sequence_index_calls.append((session, conversation_id))
        return 0


class FakeSessionScopeFactory:
    """Fake de session_scope_factory para testes."""

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestChatPersistenceService:
    """Testes para ChatPersistenceService."""

    def setup_method(self):
        """Setup comum para todos os testes."""
        self.conversation_repo = FakeConversationRepository()
        self.message_repo = FakeMessageRepository()
        self.session = FakeAsyncSession()
        self.session_scope_factory = FakeSessionScopeFactory(self.session)

        self.service = ChatPersistenceService(
            conversation_repository=self.conversation_repo,
            message_repository=self.message_repo,
            session_scope_factory=self.session_scope_factory,
        )

    # --- create_conversation ---

    @pytest.mark.asyncio
    async def test_create_conversation_calls_repository(self):
        """Testa que create_conversation chama o repository."""
        user_id = str(uuid.uuid4())
        result = await self.service.create_conversation(user_id=user_id, title="Test")

        assert result is not None
        assert len(self.conversation_repo.create_calls) == 1
        call = self.conversation_repo.create_calls[0]
        assert call[1] == user_id
        assert call[2] == "Test"

    @pytest.mark.asyncio
    async def test_create_conversation_with_metadata(self):
        """Testa que create_conversation aceita metadata."""
        user_id = str(uuid.uuid4())
        metadata = {"key": "value"}
        result = await self.service.create_conversation(
            user_id=user_id, title="Test", metadata=metadata
        )

        assert result is not None
        assert len(self.conversation_repo.create_calls) == 1
        call = self.conversation_repo.create_calls[0]
        assert call[3] == metadata

    # --- get_conversation_for_user ---

    @pytest.mark.asyncio
    async def test_get_conversation_for_user_calls_repository(self):
        """Testa que get_conversation_for_user chama o repository."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        await self.service.get_conversation_for_user(
            conversation_id=conv_id, user_id=user_id
        )

        assert len(self.conversation_repo.get_by_id_for_user_calls) == 1
        call = self.conversation_repo.get_by_id_for_user_calls[0]
        assert call[1] == conv_id
        assert call[2] == user_id

    @pytest.mark.asyncio
    async def test_get_conversation_for_user_returns_none_when_not_owner(self):
        """Testa que get_conversation_for_user não encontra conversa de outro."""
        conv_id = str(uuid.uuid4())
        wrong_user_id = "wrong_user"
        result = await self.service.get_conversation_for_user(
            conversation_id=conv_id, user_id=wrong_user_id
        )

        assert result is None

    # --- list_conversations_for_user ---

    @pytest.mark.asyncio
    async def test_list_conversations_for_user_calls_repository(self):
        """Testa que list_conversations_for_user chama o repository."""
        user_id = str(uuid.uuid4())
        await self.service.list_conversations_for_user(user_id=user_id)

        assert len(self.conversation_repo.list_for_user_calls) == 1
        call = self.conversation_repo.list_for_user_calls[0]
        assert call[1] == user_id
        assert call[2] is False  # include_archived=False por padrão

    @pytest.mark.asyncio
    async def test_list_conversations_for_user_includes_archived_when_flagged(self):
        """Testa que list_conversations_for_user inclui arquivadas com include_archived."""  # noqa: E501
        user_id = str(uuid.uuid4())
        await self.service.list_conversations_for_user(
            user_id=user_id, include_archived=True
        )

        assert len(self.conversation_repo.list_for_user_calls) == 1
        call = self.conversation_repo.list_for_user_calls[0]
        assert call[2] is True  # include_archived=True

    # --- archive_conversation_for_user ---

    @pytest.mark.asyncio
    async def test_archive_conversation_for_user_calls_repository(self):
        """Testa que archive_conversation_for_user chama o repository."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        await self.service.archive_conversation_for_user(
            conversation_id=conv_id, user_id=user_id
        )

        assert len(self.conversation_repo.archive_for_user_calls) == 1
        call = self.conversation_repo.archive_for_user_calls[0]
        assert call[1] == conv_id
        assert call[2] == user_id

    # --- add_message_for_user ---

    @pytest.mark.asyncio
    async def test_add_message_for_user_validates_role(self):
        """Testa que add_message_for_user levanta ValueError para role inválido."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Role inválido"):
            await self.service.add_message_for_user(
                conversation_id=conv_id,
                user_id=user_id,
                role="invalid_role",
                content="Test",
            )

    @pytest.mark.asyncio
    async def test_add_message_for_user_validates_conversation_ownership(self):
        """Testa que add_message_for_user levanta ValueError se conversa não pertence."""  # noqa: E501
        conv_id = str(uuid.uuid4())
        wrong_user_id = "wrong_user"

        with pytest.raises(ValueError, match="Conversa não encontrada ou não pertence"):
            await self.service.add_message_for_user(
                conversation_id=conv_id,
                user_id=wrong_user_id,
                role="user",
                content="Test",
            )

    @pytest.mark.asyncio
    async def test_add_message_for_user_calls_sequence_index_and_create(self):
        """Testa que add_message_for_user chama get_next_sequence_index e create."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        await self.service.add_message_for_user(
            conversation_id=conv_id,
            user_id=user_id,
            role="user",
            content="Hello",
            model="gpt-4",
            metadata={"key": "value"},
        )

        # Verifica que get_next_sequence_index foi chamado
        assert len(self.message_repo.get_next_sequence_index_calls) == 1
        call = self.message_repo.get_next_sequence_index_calls[0]
        assert call[1] == conv_id

        # Verifica que create foi chamado
        assert len(self.message_repo.create_calls) == 1
        call = self.message_repo.create_calls[0]
        assert call[1] == conv_id
        assert call[2] == "user"
        assert call[3] == "Hello"
        assert call[4] == 0  # sequence_index
        assert call[5] == "gpt-4"
        assert call[6] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_add_message_for_user_allows_valid_roles(self):
        """Testa que add_message_for_user aceita todos os roles permitidos."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        valid_roles = ["user", "assistant", "system", "tool"]

        for role in valid_roles:
            await self.service.add_message_for_user(
                conversation_id=conv_id,
                user_id=user_id,
                role=role,
                content="Test",
            )

    # --- list_messages_for_user ---

    @pytest.mark.asyncio
    async def test_list_messages_for_user_validates_conversation_ownership(self):
        """Testa que list_messages_for_user levanta ValueError se conversa não pertence."""  # noqa: E501
        conv_id = str(uuid.uuid4())
        wrong_user_id = "wrong_user"

        with pytest.raises(ValueError, match="Conversa não encontrada ou não pertence"):
            await self.service.list_messages_for_user(
                conversation_id=conv_id, user_id=wrong_user_id
            )

    @pytest.mark.asyncio
    async def test_list_messages_for_user_calls_repository(self):
        """Testa que list_messages_for_user chama o repository."""
        conv_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        await self.service.list_messages_for_user(
            conversation_id=conv_id, user_id=user_id
        )

        assert len(self.conversation_repo.get_by_id_for_user_calls) == 1
        assert len(self.message_repo.list_for_conversation_calls) == 1
        call = self.message_repo.list_for_conversation_calls[0]
        assert call[1] == conv_id

    # --- default session_scope_factory ---

    def test_init_uses_default_session_scope_when_not_provided(self):
        """Testa que __init__ usa session_scope padrão quando não fornecido."""
        service = ChatPersistenceService()

        # Verifica que o factory é o session_scope padrão
        assert service.session_scope_factory.__name__ == "session_scope"

    def test_init_uses_default_repositories_when_not_provided(self):
        """Testa que __init__ usa repositories padrão quando não fornecidos."""
        service = ChatPersistenceService()

        assert isinstance(service.conversation_repository, ChatConversationRepository)
        assert isinstance(service.message_repository, ChatMessageRepository)
