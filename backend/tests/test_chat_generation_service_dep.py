"""Testes para a dependency get_chat_generation_service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from labia_chat.api.deps import get_chat_generation_service
from labia_chat.services.chat_generation import ChatGenerationService
from labia_chat.services.vllm_client import VLLMClient


class TestGetChatGenerationService:
    """Testes para get_chat_generation_service."""

    @pytest.mark.asyncio
    async def test_uses_vllm_client_as_async_context_manager(self):
        """Testa que a dependency usa VLLMClient como async context manager."""
        # Mock do VLLMClient para verificar __aenter__ e __aexit__
        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client.__aenter__ = AsyncMock(return_value=mock_vllm_client)
        mock_vllm_client.__aexit__ = AsyncMock(return_value=None)

        # Mock do generate para retornar uma resposta fake
        mock_vllm_client.generate = AsyncMock(return_value="Test response")

        with patch(
            "labia_chat.api.deps.VLLMClient", return_value=mock_vllm_client
        ):
            # A dependency é um async generator, então usamos async for
            async for service in get_chat_generation_service():
                # Verifica que o service é um ChatGenerationService
                assert isinstance(service, ChatGenerationService)
                # Verifica que o service usa o client mockado
                assert service.vllm_client is mock_vllm_client

        # Verifica que __aenter__ foi chamado
        mock_vllm_client.__aenter__.assert_awaited_once()
        # Verifica que __aexit__ foi chamado (limpeza)
        mock_vllm_client.__aexit__.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_correct_parameters_to_vllm_client(self):
        """Testa que a dependency passa os parâmetros corretos ao VLLMClient."""
        from labia_chat.core.config import settings

        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client.__aenter__ = AsyncMock(return_value=mock_vllm_client)
        mock_vllm_client.__aexit__ = AsyncMock(return_value=None)

        mock_vllm_client_constructor = MagicMock(return_value=mock_vllm_client)

        with patch(
            "labia_chat.api.deps.VLLMClient", mock_vllm_client_constructor
        ):
            async for _ in get_chat_generation_service():
                pass

        # Verifica que VLLMClient foi chamado com os parâmetros corretos
        mock_vllm_client_constructor.assert_called_once_with(
            base_url=settings.vllm_base_url,
            model=settings.vllm_model,
            timeout=settings.vllm_timeout_seconds,
            api_key=settings.vllm_api_key,
        )

    @pytest.mark.asyncio
    async def test_service_uses_opened_client(self):
        """Testa que o service gerado usa o client aberto (não levanta RuntimeError)."""
        # Mock do VLLMClient com _client definido (como após __aenter__)
        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client.__aenter__ = AsyncMock(return_value=mock_vllm_client)
        mock_vllm_client.__aexit__ = AsyncMock(return_value=None)
        # Simula que o client foi aberto (como em __aenter__)
        mock_vllm_client._client = MagicMock()

        with patch(
            "labia_chat.api.deps.VLLMClient", return_value=mock_vllm_client
        ):
            async for service in get_chat_generation_service():
                # O service deve ter acesso ao client aberto
                assert service.vllm_client is mock_vllm_client
                # O client deve ter _client definido (como após __aenter__)
                assert mock_vllm_client._client is not None

    @pytest.mark.asyncio
    async def test_cleans_up_client_after_use(self):
        """Testa que o client é fechado após o uso da dependency."""
        mock_vllm_client = MagicMock(spec=VLLMClient)
        mock_vllm_client.__aenter__ = AsyncMock(return_value=mock_vllm_client)
        mock_vllm_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "labia_chat.api.deps.VLLMClient", return_value=mock_vllm_client
        ):
            async for _ in get_chat_generation_service():
                pass

        # Verifica que __aexit__ foi chamado para limpeza
        mock_vllm_client.__aexit__.assert_awaited_once()

