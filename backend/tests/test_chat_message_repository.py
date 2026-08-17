"""Testes unitários para o repositório ChatMessageRepository."""

import uuid
from unittest.mock import MagicMock

import pytest

from labia_chat.repositories.chat_message import ChatMessageRepository


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


class TestChatMessageRepository:
    """Testes para ChatMessageRepository."""

    def setup_method(self):
        """Setup comum para todos os testes."""
        self.repo = ChatMessageRepository()
        self.session = FakeAsyncSession()

    # --- create ---

    @pytest.mark.asyncio
    async def test_create_returns_message(self):
        """Testa que create retorna uma mensagem."""
        result = await self.repo.create(
            self.session,
            conversation_id=str(uuid.uuid4()),
            role="user",
            content="Hello",
            sequence_index=0,
        )

        assert result is not None
        assert result.role == "user"
        assert result.content == "Hello"
        assert result.sequence_index == 0
        assert result.message_metadata == {}

    @pytest.mark.asyncio
    async def test_create_adds_to_session(self):
        """Testa que create adiciona à sessão."""
        await self.repo.create(
            self.session,
            conversation_id=str(uuid.uuid4()),
            role="user",
            content="Hello",
            sequence_index=0,
        )

        assert len(self.session.added_objects) == 1

    @pytest.mark.asyncio
    async def test_create_with_model_and_metadata(self):
        """Testa que create aceita model e metadata."""
        result = await self.repo.create(
            self.session,
            conversation_id=str(uuid.uuid4()),
            role="assistant",
            content="Hi there",
            sequence_index=1,
            model="gpt-4",
            metadata={"key": "value"},
        )

        assert result.model == "gpt-4"
        assert result.message_metadata == {"key": "value"}

    # --- list_for_conversation ---

    @pytest.mark.asyncio
    async def test_list_for_conversation_returns_list(self):
        """Testa que list_for_conversation retorna lista."""
        fake_messages = [MagicMock(), MagicMock()]
        self.session.scalars_results = fake_messages

        result = await self.repo.list_for_conversation(
            self.session, str(uuid.uuid4())
        )

        assert result == fake_messages

    @pytest.mark.asyncio
    async def test_list_for_conversation_orders_by_sequence_index_asc(self):
        """Testa que list_for_conversation ordena por sequence_index asc."""
        await self.repo.list_for_conversation(self.session, str(uuid.uuid4()))

        query_str = str(self.session.queries[0])
        assert "sequence_index ASC" in query_str

    @pytest.mark.asyncio
    async def test_list_for_conversation_keeps_offset_pagination_semantics(self):
        """Testa que list_for_conversation mantém paginação limit/offset asc."""
        await self.repo.list_for_conversation(
            self.session, str(uuid.uuid4()), limit=50, offset=0
        )

        query_str = str(self.session.queries[0])
        # A lista pública continua cronológica com OFFSET/LIMIT (não seleção recente)
        assert "sequence_index ASC" in query_str
        assert "LIMIT :param_1" in query_str
        assert "OFFSET :param_2" in query_str

    # --- list_recent_for_conversation ---

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_orders_by_sequence_index_desc(self):
        """Testa que list_recent_for_conversation seleciona por sequence_index desc."""
        await self.repo.list_recent_for_conversation(self.session, str(uuid.uuid4()))

        query_str = str(self.session.queries[0])
        assert "sequence_index DESC" in query_str

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_restores_chronological_order(self):
        """Testa que list_recent_for_conversation retorna em ordem cronológica asc."""
        fake_messages = [MagicMock(), MagicMock()]
        self.session.scalars_results = fake_messages

        result = await self.repo.list_recent_for_conversation(
            self.session, str(uuid.uuid4())
        )

        assert result == list(reversed(fake_messages))

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_default_limit_50(self):
        """Testa que list_recent_for_conversation usa limit 50 por padrão."""
        await self.repo.list_recent_for_conversation(self.session, str(uuid.uuid4()))

        query_str = str(self.session.queries[0])
        assert "LIMIT :param_1" in query_str

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_returns_all_when_under_limit(self):
        """Testa que com 50 mensagens e limit 50 todas são retornadas (0..49)."""
        fake_messages = [MagicMock() for _ in range(50)]
        self.session.scalars_results = fake_messages

        result = await self.repo.list_recent_for_conversation(
            self.session, str(uuid.uuid4()), limit=50
        )

        assert len(result) == 50

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_fifty_one_stored_selects_newest_fifty(
        self,
    ):
        """Testa que com 51 mensagens e limit 50 são retornadas as 50 mais recentes."""
        # Simula o resultado do banco já ordenado por sequence_index desc (50..1);
        # o repositório deve devolver essas 50 em ordem cronológica (1..50).
        stored = [MagicMock(sequence_index=index) for index in range(51)]
        self.session.scalars_results = list(reversed(stored[1:]))  # DESC: 50..1

        result = await self.repo.list_recent_for_conversation(
            self.session, str(uuid.uuid4()), limit=50
        )

        # A mensagem mais antiga (índice 0) fica fora; as 50 restantes voltam asc.
        assert len(result) == 50
        assert [m.sequence_index for m in result] == list(range(1, 51))

    @pytest.mark.asyncio
    async def test_list_recent_for_conversation_limit_1_returns_newest_only(self):
        """Testa que limit 1 retorna apenas a mensagem mais recente."""
        newest = MagicMock()
        self.session.scalars_results = [newest]

        result = await self.repo.list_recent_for_conversation(
            self.session, str(uuid.uuid4()), limit=1
        )

        assert result == [newest]

    # --- get_next_sequence_index ---

    @pytest.mark.asyncio
    async def test_get_next_sequence_index_returns_0_when_no_messages(self):
        """Testa que get_next_sequence_index retorna 0 quando não há mensagens."""
        self.session.scalar_results = [None]

        result = await self.repo.get_next_sequence_index(
            self.session, str(uuid.uuid4())
        )

        assert result == 0

    @pytest.mark.asyncio
    async def test_get_next_sequence_index_returns_max_plus_1(self):
        """Testa que get_next_sequence_index retorna max + 1."""
        self.session.scalar_results = [5]

        result = await self.repo.get_next_sequence_index(
            self.session, str(uuid.uuid4())
        )

        assert result == 6

    @pytest.mark.asyncio
    async def test_get_next_sequence_index_returns_1_when_max_is_0(self):
        """Testa que get_next_sequence_index retorna 1 quando max é 0."""
        self.session.scalar_results = [0]

        result = await self.repo.get_next_sequence_index(
            self.session, str(uuid.uuid4())
        )

        assert result == 1
