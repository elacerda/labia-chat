"""Testes para a dependency get_chat_completion_service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from labia_chat.api.deps import (
    get_chat_completion_service,
    get_chat_generation_service,
)
from labia_chat.services.chat_completion import ChatCompletionService
from labia_chat.services.chat_generation import ChatGenerationService
from labia_chat.services.chat_persistence import ChatPersistenceService
from labia_chat.services.vllm_client import VLLMClient


class TestGetChatCompletionService:
    """Testes para get_chat_completion_service."""

    @pytest.mark.asyncio
    async def test_uses_injected_generation_service_with_opened_client(self):
        """Testa que a dependency usa o ChatGenerationService injetado com client aberto."""  # noqa: E501
        # Mock do VLLMClient com _client definido (como após __aenter__)
        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client._client = MagicMock()  # Simula client aberto

        # Mock do ChatGenerationService usando o client mockado
        mock_generation_service = MagicMock(spec=ChatGenerationService)
        mock_generation_service.vllm_client = mock_vllm_client

        # Mock do ChatPersistenceService
        mock_persistence_service = MagicMock(spec=ChatPersistenceService)

        # Chama get_chat_completion_service com os services mockados
        result = await get_chat_completion_service(
            persistence_service=mock_persistence_service,
            generation_service=mock_generation_service,
        )

        # Verifica que o resultado é um ChatCompletionService
        assert isinstance(result, ChatCompletionService)
        # Verifica que o service usa o persistence_service injetado
        assert result.persistence_service is mock_persistence_service
        # Verifica que o service usa o generation_service injetado
        assert result.generation_service is mock_generation_service
        # Verifica que o generation_service usa o vllm_client injetado
        assert result.generation_service.vllm_client is mock_vllm_client
        # Verifica que o vllm_client tem _client definido (como após __aenter__)
        assert mock_vllm_client._client is not None

    @pytest.mark.asyncio
    async def test_uses_injected_generation_service_not_default(self):
        """Testa que a dependency usa o generation_service injetado, não cria default."""  # noqa: E501
        # Mock do VLLMClient que não é uma instância real
        mock_vllm_client = object()  # Objeto arbitrário que não é VLLMClient

        # Mock do ChatGenerationService usando o client mockado
        mock_generation_service = MagicMock(spec=ChatGenerationService)
        mock_generation_service.vllm_client = mock_vllm_client

        # Mock do ChatPersistenceService
        mock_persistence_service = MagicMock(spec=ChatPersistenceService)

        # Chama get_chat_completion_service com os services mockados
        result = await get_chat_completion_service(
            persistence_service=mock_persistence_service,
            generation_service=mock_generation_service,
        )

        # Verifica que o generation_service usado é o injetado (não default)
        assert result.generation_service.vllm_client is mock_vllm_client

    @pytest.mark.asyncio
    async def test_uses_injected_generation_service_from_context_manager(self):
        """Testa que a dependency usa o generation_service com client aberto via context manager."""  # noqa: E501
        # Mock do VLLMClient como async context manager
        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client.__aenter__ = AsyncMock(return_value=mock_vllm_client)
        mock_vllm_client.__aexit__ = AsyncMock(return_value=None)
        mock_vllm_client._client = MagicMock()  # Simula client aberto

        with patch(
            "labia_chat.api.deps.VLLMClient", return_value=mock_vllm_client
        ):
            # Simula o comportamento de get_chat_generation_service
            async for service in get_chat_generation_service():
                # Chama get_chat_completion_service com o generation_service aberto
                persistence_service = ChatPersistenceService()
                result = await get_chat_completion_service(
                    persistence_service=persistence_service,
                    generation_service=service,
                )

                # Verifica que o resultado usa o generation_service com client aberto
                assert isinstance(result, ChatCompletionService)
                assert result.generation_service.vllm_client is mock_vllm_client
                # Verifica que o client foi aberto (como em __aenter__)
                assert mock_vllm_client._client is not None
                # Verifica que o context manager foi usado
                mock_vllm_client.__aenter__.assert_awaited_once()
                mock_vllm_client.__aexit__.assert_not_awaited()
                break  # Sai do loop após o primeiro service

