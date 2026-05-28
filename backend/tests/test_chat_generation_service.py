"""Testes unitários para o ChatGenerationService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest import approx

from labia_chat.core.config import settings
from labia_chat.services.chat_generation import (
    ChatGenerationError,
    ChatGenerationService,
)
from labia_chat.services.vllm_client import VLLMClient, VLLMClientError


class FakeVLLMClient:
    """Fake de VLLMClient para testes sem rede."""

    def __init__(self):
        self.generate_calls = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> str:
        """Simula generate e armazena a chamada."""
        self.generate_calls.append((messages, temperature, max_tokens))
        return "Test response"


class TestChatGenerationService:
    """Testes para ChatGenerationService."""

    def setup_method(self):
        """Setup comum para todos os testes."""
        self.vllm_client = FakeVLLMClient()
        self.service = ChatGenerationService(vllm_client=self.vllm_client)

    def test_init_uses_config_defaults_when_not_provided(self):
        """Testa que __init__ usa config defaults quando não fornecidos."""
        # Cria service sem parâmetros explícitos
        service = ChatGenerationService(vllm_client=self.vllm_client)

        # Deve usar os defaults do settings
        assert service.temperature == settings.vllm_temperature
        assert service.max_tokens == settings.vllm_max_tokens

    def test_init_uses_provided_params_over_config(self):
        """Testa que __init__ usa parâmetros explícitos quando fornecidos."""
        service = ChatGenerationService(
            vllm_client=self.vllm_client,
            temperature=0.8,
            max_tokens=1024,
        )

        assert service.temperature == 0.8
        assert service.max_tokens == 1024

    # --- generate success ---

    @pytest.mark.asyncio
    async def test_generate_success_uses_config_defaults(self):
        """Testa geração bem-sucedida usando config defaults."""
        messages = [{"role": "user", "content": "Hello"}]
        result = await self.service.generate(messages=messages)

        assert result == "Test response"
        assert len(self.vllm_client.generate_calls) == 1
        call = self.vllm_client.generate_calls[0]
        assert call[0] == messages
        # Deve usar os defaults do settings
        assert call[1] == approx(settings.vllm_temperature)
        assert call[2] == approx(settings.vllm_max_tokens)

    @pytest.mark.asyncio
    async def test_generate_with_explicit_params_overrides_config(self):
        """Testa que parâmetros explícitos sobrescrevem config."""
        messages = [{"role": "user", "content": "Hello"}]
        result = await self.service.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )

        assert result == "Test response"
        assert len(self.vllm_client.generate_calls) == 1
        call = self.vllm_client.generate_calls[0]
        assert call[1] == 0.7
        assert call[2] == 100

    @pytest.mark.asyncio
    async def test_generate_multiple_messages(self):
        """Testa geração com múltiplas mensagens."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        result = await self.service.generate(messages=messages)

        assert result == "Test response"
        assert len(self.vllm_client.generate_calls) == 1
        call = self.vllm_client.generate_calls[0]
        assert call[0] == messages

    # --- messages vazio ---

    @pytest.mark.asyncio
    async def test_generate_empty_messages(self):
        """Testa que generate levanta erro para messages vazio."""
        service = ChatGenerationService(vllm_client=self.vllm_client)

        with pytest.raises(ChatGenerationError, match="messages cannot be empty"):
            await service.generate(messages=[])

    # --- mensagem sem role ---

    @pytest.mark.asyncio
    async def test_generate_message_without_role(self):
        """Testa que generate levanta erro para mensagem sem role."""
        messages = [{"content": "Hello"}]

        with pytest.raises(ChatGenerationError, match="must have 'role' key"):
            await self.service.generate(messages=messages)

    # --- mensagem sem content ---

    @pytest.mark.asyncio
    async def test_generate_message_without_content(self):
        """Testa que generate levanta erro para mensagem sem content."""
        messages = [{"role": "user"}]

        with pytest.raises(ChatGenerationError, match="must have 'content' key"):
            await self.service.generate(messages=messages)

    # --- role inválida ---

    @pytest.mark.asyncio
    async def test_generate_invalid_role(self):
        """Testa que generate levanta erro para role inválida."""
        messages = [{"role": "invalid_role", "content": "Hello"}]

        with pytest.raises(ChatGenerationError, match="Invalid role"):
            await self.service.generate(messages=messages)

    @pytest.mark.asyncio
    async def test_generate_all_valid_roles(self):
        """Testa que generate aceita todos os roles permitidos."""
        valid_roles = ["user", "assistant", "system", "tool"]

        for role in valid_roles:
            messages = [{"role": role, "content": "Hello"}]
            result = await self.service.generate(messages=messages)
            assert result == "Test response"

    # --- content vazio ---

    @pytest.mark.asyncio
    async def test_generate_empty_content(self):
        """Testa que generate levanta erro para content vazio."""
        messages = [{"role": "user", "content": ""}]

        with pytest.raises(
            ChatGenerationError, match="cannot be empty or whitespace only"
        ):
            await self.service.generate(messages=messages)

    @pytest.mark.asyncio
    async def test_generate_whitespace_content(self):
        """Testa que generate levanta erro para content com apenas whitespace."""
        messages = [{"role": "user", "content": "   "}]

        with pytest.raises(
            ChatGenerationError, match="cannot be empty or whitespace only"
        ):
            await self.service.generate(messages=messages)

    # --- tipo inválido ---

    @pytest.mark.asyncio
    async def test_generate_message_not_dict(self):
        """Testa que generate levanta erro para mensagem que não é dict."""
        messages = ["not a dict"]

        with pytest.raises(ChatGenerationError, match="must be a dictionary"):
            await self.service.generate(messages=messages)

    @pytest.mark.asyncio
    async def test_generate_role_not_string(self):
        """Testa que generate levanta erro para role que não é string."""
        messages = [{"role": 123, "content": "Hello"}]

        with pytest.raises(ChatGenerationError, match="must be a string"):
            await self.service.generate(messages=messages)

    @pytest.mark.asyncio
    async def test_generate_content_not_string(self):
        """Testa que generate levanta erro para content que não é string."""
        messages = [{"role": "user", "content": 123}]

        with pytest.raises(ChatGenerationError, match="must be a string"):
            await self.service.generate(messages=messages)

    # --- erro do VLLMClient ---

    @pytest.mark.asyncio
    async def test_generate_vllm_client_error(self):
        """Testa que erro do VLLMClient é convertido em ChatGenerationError."""
        fake_client = MagicMock(spec=VLLMClient)
        fake_client.generate = AsyncMock(
            side_effect=VLLMClientError("Connection failed")
        )
        service = ChatGenerationService(vllm_client=fake_client)

        with pytest.raises(
            ChatGenerationError, match="VLLM failed to generate response"
        ):
            await service.generate(messages=[{"role": "user", "content": "Hello"}])

    @pytest.mark.asyncio
    async def test_generate_vllm_client_error_preserves_original_message(self):
        """Testa que erro do VLLMClient preserva a mensagem original."""
        fake_client = MagicMock(spec=VLLMClient)
        fake_client.generate = AsyncMock(
            side_effect=VLLMClientError("Model not found")
        )
        service = ChatGenerationService(vllm_client=fake_client)

        with pytest.raises(ChatGenerationError, match="Model not found"):
            await service.generate(messages=[{"role": "user", "content": "Hello"}])

    # --- default vllm_client ---

    def test_init_uses_default_vllm_client_when_not_provided(self):
        """Testa que __init__ usa VLLMClient padrão quando não fornecido."""
        service = ChatGenerationService()

        assert isinstance(service.vllm_client, VLLMClient)

