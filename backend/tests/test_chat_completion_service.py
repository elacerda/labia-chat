"""Testes unitários para o ChatCompletionService."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from labia_chat.services.chat_completion import (
    ChatCompletionError,
    ChatCompletionGenerationError,
    ChatCompletionService,
)
from labia_chat.services.chat_generation import (
    ChatGenerationError,
    ChatGenerationService,
)
from labia_chat.services.chat_persistence import ChatPersistenceService


class FakePersistenceService:
    """Fake de ChatPersistenceService para testes sem banco."""

    def __init__(self):
        self.get_conversation_for_user_calls = []
        self.add_message_for_user_calls = []
        self.list_messages_for_user_calls = []

        # Valores de retorno para os métodos
        self.get_conversation_for_user_return = None
        self.add_message_for_user_return = None
        self.list_messages_for_user_return = []

    async def get_conversation_for_user(self, conversation_id, user_id):
        """Simula get_conversation_for_user."""
        self.get_conversation_for_user_calls.append(
            (conversation_id, user_id)
        )
        return self.get_conversation_for_user_return

    async def add_message_for_user(
        self,
        conversation_id,
        user_id,
        role,
        content,
        model=None,
        metadata=None,
    ):
        """Simula add_message_for_user."""
        self.add_message_for_user_calls.append(
            (conversation_id, user_id, role, content, model, metadata)
        )
        return self.add_message_for_user_return

    async def list_messages_for_user(self, conversation_id, user_id):
        """Simula list_messages_for_user."""
        self.list_messages_for_user_calls.append(
            (conversation_id, user_id)
        )
        return self.list_messages_for_user_return


class FakeGenerationService:
    """Fake de ChatGenerationService para testes sem VLLM."""

    def __init__(self):
        self.generate_calls = []
        self.generate_stream_calls = []
        self.generate_return = "Test response"
        self.generate_stream_chunks = ["Test ", "response"]

    async def generate(self, messages):
        """Simula generate e armazena a chamada."""
        self.generate_calls.append(messages)
        return self.generate_return

    async def generate_stream(self, messages):
        """Simula generate_stream e armazena a chamada."""
        self.generate_stream_calls.append(messages)
        for chunk in self.generate_stream_chunks:
            yield chunk


class FakeChatMessage:
    """Fake de ChatMessage para testes."""

    def __init__(self, id, conversation_id, role, content, sequence_index, model=None):
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.sequence_index = sequence_index
        self.model = model


class TestChatCompletionService:
    """Testes para ChatCompletionService."""

    def setup_method(self):
        """Setup comum para todos os testes."""
        self.persistence_service = FakePersistenceService()
        self.generation_service = FakeGenerationService()
        self.service = ChatCompletionService(
            persistence_service=self.persistence_service,
            generation_service=self.generation_service,
        )

        self.conversation_id = str(uuid.uuid4())
        self.user_id = str(uuid.uuid4())

    # --- sucesso ---

    @pytest.mark.asyncio
    async def test_complete_success(self):
        """Testa sucesso: persiste user, lista histórico, chama geração,
        persiste assistant, salva model correto, retorna assistant."""
        # Configura fake persistence service
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_assistant_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="assistant",
            content="Test response",
            sequence_index=1,
            model="qwen-coder-next",
        )
        self.persistence_service.add_message_for_user_return = fake_assistant_message

        fake_messages = [
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="user",
                content="Hello",
                sequence_index=0,
            ),
        ]
        self.persistence_service.list_messages_for_user_return = fake_messages

        # Chama complete
        result = await self.service.complete(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model="qwen-coder-next",
        )

        # Verifica que get_conversation_for_user foi chamado
        assert len(self.persistence_service.get_conversation_for_user_calls) == 1
        call = self.persistence_service.get_conversation_for_user_calls[0]
        assert call[0] == self.conversation_id
        assert call[1] == self.user_id

        # Verifica que add_message_for_user foi chamado para user
        assert len(self.persistence_service.add_message_for_user_calls) == 2

        # Primeira chamada deve ser para user
        user_call = self.persistence_service.add_message_for_user_calls[0]
        assert user_call[0] == self.conversation_id
        assert user_call[1] == self.user_id
        assert user_call[2] == "user"
        assert user_call[3] == "Hello"
        assert user_call[4] is None  # model=None para user
        assert user_call[5] is None  # metadata=None

        # Segunda chamada deve ser para assistant
        assistant_call = self.persistence_service.add_message_for_user_calls[1]
        assert assistant_call[0] == self.conversation_id
        assert assistant_call[1] == self.user_id
        assert assistant_call[2] == "assistant"
        assert assistant_call[3] == "Test response"
        assert assistant_call[4] == "qwen-coder-next"  # model correto
        assert assistant_call[5] is None  # metadata=None

        # Verifica que list_messages_for_user foi chamado
        assert len(self.persistence_service.list_messages_for_user_calls) == 1
        call = self.persistence_service.list_messages_for_user_calls[0]
        assert call[0] == self.conversation_id
        assert call[1] == self.user_id

        # Verifica que generate foi chamado com mensagens em ordem
        assert len(self.generation_service.generate_calls) == 1
        messages = self.generation_service.generate_calls[0]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

        # Verifica que o resultado é a mensagem assistant
        assert result == fake_assistant_message
        assert result.role == "assistant"
        assert result.content == "Test response"
        assert result.model == "qwen-coder-next"

    @pytest.mark.asyncio
    async def test_complete_success_default_model(self):
        """Testa sucesso com model=None (usa None na mensagem assistant)."""
        # Configura fake persistence service
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_assistant_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="assistant",
            content="Test response",
            sequence_index=1,
            model=None,
        )
        self.persistence_service.add_message_for_user_return = fake_assistant_message

        fake_messages = [
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="user",
                content="Hello",
                sequence_index=0,
            ),
        ]
        self.persistence_service.list_messages_for_user_return = fake_messages

        # Chama complete sem model
        result = await self.service.complete(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model=None,
        )

        # Verifica que generate foi chamado
        assert len(self.generation_service.generate_calls) == 1

        # Verifica que add_message_for_user foi chamado para assistant com model=None
        assistant_call = self.persistence_service.add_message_for_user_calls[1]
        assert assistant_call[4] is None  # model=None

        # Verifica que o resultado tem model=None
        assert result.model is None

    @pytest.mark.asyncio
    async def test_complete_stream_success_streams_then_persists_assistant(self):
        """Testa stream: persiste user, streama chunks, persiste assistant no fim."""
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_user_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="user",
            content="Hello",
            sequence_index=0,
        )
        fake_assistant_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="assistant",
            content="Test response",
            sequence_index=1,
            model="qwen-coder-next",
        )
        self.persistence_service.add_message_for_user_return = fake_user_message
        self.persistence_service.list_messages_for_user_return = [fake_user_message]

        stream = await self.service.complete_stream(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model="qwen-coder-next",
        )

        events = []
        async for event in stream:
            if event[0] == "text" and len(events) == 1:
                self.persistence_service.add_message_for_user_return = (
                    fake_assistant_message
                )
            events.append(event)

        assert events == [
            ("text", "Test "),
            ("text", "response"),
            ("done", str(fake_assistant_message.id)),
        ]
        assert len(self.persistence_service.add_message_for_user_calls) == 2
        user_call = self.persistence_service.add_message_for_user_calls[0]
        assistant_call = self.persistence_service.add_message_for_user_calls[1]
        assert user_call[2] == "user"
        assert assistant_call[2] == "assistant"
        assert assistant_call[3] == "Test response"
        assert assistant_call[4] == "qwen-coder-next"
        assert self.generation_service.generate_stream_calls == [
            [{"role": "user", "content": "Hello"}]
        ]

    @pytest.mark.asyncio
    async def test_complete_stream_partial_error_does_not_persist_assistant(
        self,
    ):
        """Testa que erro após chunks parciais não persiste assistant."""
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_user_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="user",
            content="Hello",
            sequence_index=0,
        )
        self.persistence_service.add_message_for_user_return = fake_user_message
        self.persistence_service.list_messages_for_user_return = [fake_user_message]

        async def failing_stream(messages):
            self.generation_service.generate_stream_calls.append(messages)
            yield "partial"
            raise ChatGenerationError("raw upstream failure")

        self.generation_service.generate_stream = failing_stream

        stream = await self.service.complete_stream(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model="qwen-coder-next",
        )

        events = []
        with pytest.raises(
            ChatCompletionGenerationError, match="Failed to generate response"
        ):
            async for event in stream:
                events.append(event)

        assert events == [("text", "partial")]
        assert len(self.persistence_service.add_message_for_user_calls) == 1
        assert self.persistence_service.add_message_for_user_calls[0][2] == "user"

    @pytest.mark.asyncio
    async def test_complete_stream_cancelled_after_partial_does_not_persist_assistant(
        self,
    ):
        """Testa que cancelamento propaga e não persiste assistant parcial."""
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_user_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="user",
            content="Hello",
            sequence_index=0,
        )
        self.persistence_service.add_message_for_user_return = fake_user_message
        self.persistence_service.list_messages_for_user_return = [fake_user_message]

        async def cancelled_stream(messages):
            self.generation_service.generate_stream_calls.append(messages)
            yield "partial"
            raise asyncio.CancelledError()

        self.generation_service.generate_stream = cancelled_stream

        stream = await self.service.complete_stream(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model="qwen-coder-next",
        )

        events = []
        with pytest.raises(asyncio.CancelledError):
            async for event in stream:
                events.append(event)

        assert events == [("text", "partial")]
        assert len(self.persistence_service.add_message_for_user_calls) == 1
        assert self.persistence_service.add_message_for_user_calls[0][2] == "user"

    @pytest.mark.asyncio
    async def test_complete_stream_empty_success_does_not_persist_assistant(self):
        """Testa que stream bem-sucedido vazio é tratado como falha."""
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_user_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="user",
            content="Hello",
            sequence_index=0,
        )
        self.persistence_service.add_message_for_user_return = fake_user_message
        self.persistence_service.list_messages_for_user_return = [fake_user_message]
        self.generation_service.generate_stream_chunks = []

        stream = await self.service.complete_stream(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="Hello",
            model="qwen-coder-next",
        )

        events = []
        with pytest.raises(
            ChatCompletionGenerationError, match="Failed to generate response"
        ):
            async for event in stream:
                events.append(event)

        assert events == []
        assert len(self.persistence_service.add_message_for_user_calls) == 1
        assert self.persistence_service.add_message_for_user_calls[0][2] == "user"

    @pytest.mark.asyncio
    async def test_complete_multiple_messages_in_history(self):
        """Testa sucesso com múltiplas mensagens no histórico."""
        # Configura fake persistence service
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_assistant_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="assistant",
            content="Test response",
            sequence_index=3,
            model="qwen-coder-next",
        )
        self.persistence_service.add_message_for_user_return = fake_assistant_message

        fake_messages = [
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="system",
                content="You are helpful.",
                sequence_index=0,
            ),
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="user",
                content="Hello",
                sequence_index=1,
            ),
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="assistant",
                content="Hi there!",
                sequence_index=2,
            ),
        ]
        self.persistence_service.list_messages_for_user_return = fake_messages

        # Chama complete
        await self.service.complete(
            conversation_id=self.conversation_id,
            user_id=self.user_id,
            content="How are you?",
            model="qwen-coder-next",
        )

        # Verifica que generate foi chamado com todas as mensagens em ordem
        assert len(self.generation_service.generate_calls) == 1
        messages = self.generation_service.generate_calls[0]
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi there!"

    # --- conversa inexistente/sem ownership ---

    @pytest.mark.asyncio
    async def test_complete_conversation_not_found(self):
        """Testa que conversa inexistente não chama geração e não persiste assistant."""
        # Configura fake persistence service para retornar None
        self.persistence_service.get_conversation_for_user_return = None

        # Chama complete e verifica que levanta ChatCompletionError
        with pytest.raises(ChatCompletionError, match="Conversation not found"):
            await self.service.complete(
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                content="Hello",
            )

        # Verifica que add_message_for_user NÃO foi chamado
        assert len(self.persistence_service.add_message_for_user_calls) == 0

        # Verifica que generate NÃO foi chamado
        assert len(self.generation_service.generate_calls) == 0

    @pytest.mark.asyncio
    async def test_complete_wrong_user(self):
        """Testa que conversa de outro usuário não chama geração."""
        # Configura fake persistence service para retornar None (simula wrong_user)
        self.persistence_service.get_conversation_for_user_return = None

        # Chama complete e verifica que levanta ChatCompletionError
        with pytest.raises(ChatCompletionError, match="Conversation not found"):
            await self.service.complete(
                conversation_id=self.conversation_id,
                user_id="wrong_user",
                content="Hello",
            )

        # Verifica que add_message_for_user NÃO foi chamado
        assert len(self.persistence_service.add_message_for_user_calls) == 0

        # Verifica que generate NÃO foi chamado
        assert len(self.generation_service.generate_calls) == 0

    # --- erro de geração ---

    @pytest.mark.asyncio
    async def test_complete_generation_error(self):
        """Testa que erro de geração mantém mensagem user e propaga erro."""
        # Configura fake persistence service
        fake_conversation = MagicMock()
        fake_conversation.id = self.conversation_id
        fake_conversation.user_id = self.user_id
        self.persistence_service.get_conversation_for_user_return = fake_conversation

        fake_user_message = FakeChatMessage(
            id=str(uuid.uuid4()),
            conversation_id=self.conversation_id,
            role="user",
            content="Hello",
            sequence_index=0,
        )
        self.persistence_service.add_message_for_user_return = fake_user_message

        fake_messages = [
            FakeChatMessage(
                id=str(uuid.uuid4()),
                conversation_id=self.conversation_id,
                role="user",
                content="Hello",
                sequence_index=0,
            ),
        ]
        self.persistence_service.list_messages_for_user_return = fake_messages

        # Configura fake generation service para levantar ChatGenerationError
        self.generation_service.generate = AsyncMock(
            side_effect=ChatGenerationError("Model not found")
        )

        # Chama complete e verifica que levanta ChatCompletionError
        with pytest.raises(
            ChatCompletionError, match="Failed to generate response: Model not found"
        ):
            await self.service.complete(
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                content="Hello",
            )

        # Verifica que add_message_for_user foi chamado para user
        assert len(self.persistence_service.add_message_for_user_calls) == 1
        user_call = self.persistence_service.add_message_for_user_calls[0]
        assert user_call[2] == "user"

        # Verifica que add_message_for_user NÃO foi chamado para assistant
        assert len(self.persistence_service.add_message_for_user_calls) == 1

        # Verifica que generate foi chamado (verifica que o mock foi chamado)
        self.generation_service.generate.assert_awaited_once()

    # --- validação de conteúdo vazio ---

    @pytest.mark.asyncio
    async def test_complete_empty_content(self):
        """Testa que conteúdo vazio é rejeitado antes de chamar geração."""
        # Chama complete com conteúdo vazio
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await self.service.complete(
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                content="",
            )

        # Verifica que get_conversation_for_user NÃO foi chamado
        assert len(self.persistence_service.get_conversation_for_user_calls) == 0

        # Verifica que add_message_for_user NÃO foi chamado
        assert len(self.persistence_service.add_message_for_user_calls) == 0

        # Verifica que generate NÃO foi chamado
        assert len(self.generation_service.generate_calls) == 0

    @pytest.mark.asyncio
    async def test_complete_whitespace_content(self):
        """Testa que conteúdo com apenas whitespace é rejeitado."""
        # Chama complete com conteúdo whitespace
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await self.service.complete(
                conversation_id=self.conversation_id,
                user_id=self.user_id,
                content="   ",
            )

        # Verifica que get_conversation_for_user NÃO foi chamado
        assert len(self.persistence_service.get_conversation_for_user_calls) == 0

        # Verifica que add_message_for_user NÃO foi chamado
        assert len(self.persistence_service.add_message_for_user_calls) == 0

        # Verifica que generate NÃO foi chamado
        assert len(self.generation_service.generate_calls) == 0

    # --- init com services padrão ---

    def test_init_uses_default_services_when_not_provided(self):
        """Testa que __init__ usa services padrão quando não fornecidos."""
        service = ChatCompletionService()

        assert isinstance(service.persistence_service, ChatPersistenceService)
        assert isinstance(service.generation_service, ChatGenerationService)
