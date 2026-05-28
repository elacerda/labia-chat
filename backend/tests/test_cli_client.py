"""Testes do cliente HTTP do CLI."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from labia_chat.cli_client import (
    AuthError,
    BackendError,
    CLIClient,
    ConnectionError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class TestCLIClientInit:
    """Testes de inicialização do CLIClient."""

    def test_init_with_url(self) -> None:
        """Testa inicialização com URL."""
        client = CLIClient("http://example.com")
        assert client.api_url == "http://example.com"
        assert client.token is None
        assert client.conversation_id is None

    def test_init_strips_trailing_slash(self) -> None:
        """Testa que URL com trailing slash é normalizada."""
        client = CLIClient("http://example.com/")
        assert client.api_url == "http://example.com"


class TestCLIClientSetToken:
    """Testes de definição de token."""

    def test_set_token(self) -> None:
        """Testa definição de token."""
        client = CLIClient("http://example.com")
        client.set_token("test-token-123")
        assert client.token == "test-token-123"


class TestCLIClientValidateToken:
    """Testes de validação de token."""

    def test_validate_token_success(self) -> None:
        """Testa validação de token bem-sucedida."""
        user_data = {
            "id": "user123",
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
            "roles": ["public", "chat_vllm"],
        }

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value.status_code = 200
            mock_client.get.return_value.json.return_value = user_data
            mock_get_client.return_value = mock_client

            result = client.validate_token()

        assert result["username"] == "testuser"
        mock_client.get.assert_called_once_with("/auth/me")

    def test_validate_token_401(self) -> None:
        """Testa validação de token inválido (401)."""
        client = CLIClient("http://example.com")
        client.set_token("invalid-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.json.return_value = {"detail": "Not authenticated"}
            # Cria HTTPStatusError com a resposta
            error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(AuthError) as exc_info:
                client.validate_token()

        assert "Token inválido ou expirado" in str(exc_info.value)

    def test_validate_token_403(self) -> None:
        """Testa validação sem permissão (403)."""
        client = CLIClient("http://example.com")
        client.set_token("no-permission-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 403
            response.json.return_value = {"detail": "Forbidden"}
            error = httpx.HTTPStatusError(
                "403 Forbidden",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(PermissionError) as exc_info:
                client.validate_token()

        assert "sem permissão chat_vllm" in str(exc_info.value)

    def test_validate_token_502(self) -> None:
        """Testa erro no backend (502)."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 502
            response.json.return_value = {"detail": "Bad Gateway"}
            error = httpx.HTTPStatusError(
                "502 Bad Gateway",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(BackendError) as exc_info:
                client.validate_token()

        assert "Backend não conseguiu obter resposta do modelo" in str(exc_info.value)


class TestCLIClientCreateConversation:
    """Testes de criação de conversa."""

    def test_create_conversation_success(self) -> None:
        """Testa criação de conversa bem-sucedida."""
        conv_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Test Conversation",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "archived_at": None,
        }

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = conv_data
            mock_client.post.return_value = response
            mock_get_client.return_value = mock_client

            result = client.create_conversation()

        assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert client.conversation_id == "123e4567-e89b-12d3-a456-426614174000"
        mock_client.post.assert_called_once_with("/chat/conversations", json={})

    def test_create_conversation_with_title(self) -> None:
        """Testa criação de conversa com título."""
        conv_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "My Title",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "archived_at": None,
        }

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = conv_data
            mock_client.post.return_value = response
            mock_get_client.return_value = mock_client

            result = client.create_conversation(title="My Title")

        assert result["title"] == "My Title"
        mock_client.post.assert_called_once_with(
            "/chat/conversations", json={"title": "My Title"}
        )

    def test_create_conversation_401(self) -> None:
        """Testa criação de conversa com token inválido (401)."""
        client = CLIClient("http://example.com")
        client.set_token("invalid-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.json.return_value = {"detail": "Not authenticated"}
            error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(AuthError) as exc_info:
                client.create_conversation()

        assert "Token inválido ou expirado" in str(exc_info.value)


class TestCLIClientGenerateMessage:
    """Testes de geração de mensagem."""

    def test_generate_message_success(self) -> None:
        """Testa geração de mensagem bem-sucedida."""
        message_data = {
            "id": "msg-123",
            "conversation_id": "conv-123",
            "role": "assistant",
            "content": "Esta é uma resposta de teste.",
            "sequence_index": 1,
            "model": "qwen-coder-next",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
        }

        client = CLIClient("http://example.com")
        client.set_token("test-token")
        client.conversation_id = "conv-123"

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 201
            response.json.return_value = message_data
            mock_client.post.return_value = response
            mock_get_client.return_value = mock_client

            result = client.generate_message("Olá, mundo!")

        assert result["content"] == "Esta é uma resposta de teste."
        mock_client.post.assert_called_once_with(
            "/chat/conversations/conv-123/generate",
            json={"content": "Olá, mundo!"},
        )

    def test_generate_message_no_conversation(self) -> None:
        """Testa geração sem conversa selecionada."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with pytest.raises(Exception) as exc_info:
            client.generate_message("Olá, mundo!")

        assert "Nenhuma conversa selecionada" in str(exc_info.value)

    def test_generate_message_404(self) -> None:
        """Testa geração com conversa não encontrada (404)."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")
        client.conversation_id = "nonexistent"

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 404
            response.json.return_value = {"detail": "Not found"}
            error = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError) as exc_info:
                client.generate_message("Olá, mundo!")

        assert "Conversa não encontrada" in str(exc_info.value)

    def test_generate_message_502(self) -> None:
        """Testa erro no backend durante geração (502)."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")
        client.conversation_id = "conv-123"

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 502
            response.json.return_value = {"detail": "Bad Gateway"}
            error = httpx.HTTPStatusError(
                "502 Bad Gateway",
                request=MagicMock(),
                response=response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(BackendError) as exc_info:
                client.generate_message("Olá, mundo!")

        assert "Backend não conseguiu obter resposta do modelo" in str(exc_info.value)


class TestCLIClientListMessages:
    """Testes de listagem de mensagens."""

    def test_list_messages_success(self) -> None:
        """Testa listagem de mensagens bem-sucedida."""
        messages_data = [
            {
                "id": "msg-1",
                "conversation_id": "conv-123",
                "role": "user",
                "content": "Olá!",
                "sequence_index": 0,
                "model": None,
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "id": "msg-2",
                "conversation_id": "conv-123",
                "role": "assistant",
                "content": "Olá! Como posso ajudar?",
                "sequence_index": 1,
                "model": "qwen-coder-next",
                "metadata": {},
                "created_at": "2024-01-01T00:00:01Z",
            },
        ]

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = messages_data
            mock_client.get.return_value = response
            mock_get_client.return_value = mock_client

            result = client.list_messages("conv-123")

        assert len(result) == 2
        assert result[0]["content"] == "Olá!"
        assert result[1]["content"] == "Olá! Como posso ajudar?"
        mock_client.get.assert_called_once_with(
            "/chat/conversations/conv-123/messages", params={"limit": 50, "offset": 0}
        )

    def test_list_messages_401(self) -> None:
        """Testa listagem de mensagens com token inválido (401)."""
        client = CLIClient("http://example.com")
        client.set_token("invalid-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.json.return_value = {"detail": "Not authenticated"}
            error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(AuthError) as exc_info:
                client.list_messages("conv-123")

        assert "Token inválido ou expirado" in str(exc_info.value)

    def test_list_messages_404(self) -> None:
        """Testa listagem de mensagens com conversa não encontrada (404)."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 404
            response.json.return_value = {"detail": "Not found"}
            error = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError) as exc_info:
                client.list_messages("conv-123")

        assert "Conversa não encontrada" in str(exc_info.value)


class TestCLIClientGetConversation:
    """Testes de obtenção de conversa."""

    def test_get_conversation_success(self) -> None:
        """Testa obtenção de conversa bem-sucedida."""
        conv_data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Test Conversation",
            "metadata": {},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "archived_at": None,
        }

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = conv_data
            mock_client.get.return_value = response
            mock_get_client.return_value = mock_client

            result = client.get_conversation("123e4567-e89b-12d3-a456-426614174000")

        assert result["id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result["title"] == "Test Conversation"
        mock_client.get.assert_called_once_with(
            "/chat/conversations/123e4567-e89b-12d3-a456-426614174000"
        )

    def test_get_conversation_401(self) -> None:
        """Testa obtenção de conversa com token inválido (401)."""
        client = CLIClient("http://example.com")
        client.set_token("invalid-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.json.return_value = {"detail": "Not authenticated"}
            error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(AuthError) as exc_info:
                client.get_conversation("123e4567-e89b-12d3-a456-426614174000")

        assert "Token inválido ou expirado" in str(exc_info.value)

    def test_get_conversation_404(self) -> None:
        """Testa obtenção de conversa não encontrada (404)."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 404
            response.json.return_value = {"detail": "Not found"}
            error = httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(NotFoundError) as exc_info:
                client.get_conversation("123e4567-e89b-12d3-a456-426614174000")

        assert "Conversa não encontrada" in str(exc_info.value)


class TestCLIClientListConversations:
    """Testes de listagem de conversas."""

    def test_list_conversations_success(self) -> None:
        """Testa listagem de conversas bem-sucedida."""
        conv_data = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Conversa 1",
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "archived_at": None,
            },
            {
                "id": "890abc12-def3-4567-8901-234567890abc",
                "title": "Conversa 2",
                "metadata": {},
                "created_at": "2024-01-02T00:00:00Z",
                "updated_at": "2024-01-02T00:00:00Z",
                "archived_at": None,
            },
        ]

        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = conv_data
            mock_client.get.return_value = response
            mock_get_client.return_value = mock_client

            result = client.list_conversations()

        assert len(result) == 2
        assert result[0]["id"] == "123e4567-e89b-12d3-a456-426614174000"
        assert result[1]["title"] == "Conversa 2"
        mock_client.get.assert_called_once_with(
            "/chat/conversations", params={"limit": 20, "offset": 0}
        )

    def test_list_conversations_empty(self) -> None:
        """Testa listagem de conversas sem resultados."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = []
            mock_client.get.return_value = response
            mock_get_client.return_value = mock_client

            result = client.list_conversations()

        assert len(result) == 0
        mock_client.get.assert_called_once_with(
            "/chat/conversations", params={"limit": 20, "offset": 0}
        )

    def test_list_conversations_401(self) -> None:
        """Testa listagem de conversas com token inválido (401)."""
        client = CLIClient("http://example.com")
        client.set_token("invalid-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 401
            response.json.return_value = {"detail": "Not authenticated"}
            error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(AuthError) as exc_info:
                client.list_conversations()

        assert "Token inválido ou expirado" in str(exc_info.value)

    def test_list_conversations_403(self) -> None:
        """Testa listagem de conversas sem permissão (403)."""
        client = CLIClient("http://example.com")
        client.set_token("no-permission-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 403
            response.json.return_value = {"detail": "Forbidden"}
            error = httpx.HTTPStatusError(
                "403 Forbidden",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(PermissionError) as exc_info:
                client.list_conversations()

        assert "sem permissão chat_vllm" in str(exc_info.value)


class TestCLIClientClose:
    """Testes de fechamento do cliente."""

    def test_close(self) -> None:
        """Testa fechamento do cliente."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")
        client._get_client()  # Cria o cliente
        client.close()
        assert client._client is None


class TestCLIClientValidationError422:
    """Testes de mapeamento HTTP 422 para ValidationError."""

    def test_validate_token_422(self) -> None:
        """Testa que HTTP 422 mapeia para ValidationError em validate_token()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 422
            response.json.return_value = {"detail": "Validation error"}
            error = httpx.HTTPStatusError(
                "422 Unprocessable Entity",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ValidationError) as exc_info:
                client.validate_token()

        assert "Dados inválidos" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_create_conversation_422(self) -> None:
        """Testa que HTTP 422 mapeia para ValidationError em create_conversation()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 422
            response.json.return_value = {"detail": "Validation error"}
            error = httpx.HTTPStatusError(
                "422 Unprocessable Entity",
                request=MagicMock(),
                response=response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ValidationError) as exc_info:
                client.create_conversation()

        assert "Dados inválidos" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_generate_message_422(self) -> None:
        """Testa que HTTP 422 mapeia para ValidationError em generate_message()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")
        client.conversation_id = "conv-123"

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 422
            response.json.return_value = {"detail": "Validation error"}
            error = httpx.HTTPStatusError(
                "422 Unprocessable Entity",
                request=MagicMock(),
                response=response,
            )
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ValidationError) as exc_info:
                client.generate_message("Olá, mundo!")

        assert "Dados inválidos" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_list_messages_422(self) -> None:
        """Testa que HTTP 422 mapeia para ValidationError em list_messages()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            response = MagicMock()
            response.status_code = 422
            response.json.return_value = {"detail": "Validation error"}
            error = httpx.HTTPStatusError(
                "422 Unprocessable Entity",
                request=MagicMock(),
                response=response,
            )
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ValidationError) as exc_info:
                client.list_messages("conv-123")

        assert "Dados inválidos" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)


class TestCLIClientConnectionError:
    """Testes de mapeamento de erros de conexão para ConnectionError."""

    def test_validate_token_timeout(self) -> None:
        """Testa que timeout mapeia para ConnectionError em validate_token()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            error = httpx.TimeoutException("Timeout")
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError) as exc_info:
                client.validate_token()

        assert "Timeout ao conectar ao backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_create_conversation_timeout(self) -> None:
        """Testa que timeout mapeia para ConnectionError em create_conversation()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            error = httpx.TimeoutException("Timeout")
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError) as exc_info:
                client.create_conversation()

        assert "Timeout ao conectar ao backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_validate_token_network_error(self) -> None:
        """Testa que erro de rede mapeia para ConnectionError em validate_token()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            error = httpx.NetworkError("Network error")
            mock_client.get.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError) as exc_info:
                client.validate_token()

        assert "Falha de conexão com o backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_create_conversation_network_error(self) -> None:
        """Testa erro de rede -> ConnectionError em create_conversation()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            error = httpx.NetworkError("Network error")
            mock_client.post.side_effect = error
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError) as exc_info:
                client.create_conversation()

        assert "Falha de conexão com o backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)


class TestCLIClientBackendError:
    """Testes de mapeamento de payload inesperado para BackendError."""

    def test_validate_token_unexpected_dict_payload(self) -> None:
        """Testa que payload inesperado mapeia para BackendError em validate_token()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value.status_code = 200
            # Retorna uma string em vez de dict
            mock_client.get.return_value.json.return_value = "unexpected string"
            mock_get_client.return_value = mock_client

            with pytest.raises(BackendError) as exc_info:
                client.validate_token()

        assert "Resposta inesperada do backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)

    def test_list_conversations_unexpected_list_payload(self) -> None:
        """Testa payload inesperado -> BackendError em list_conversations()."""
        client = CLIClient("http://example.com")
        client.set_token("test-token")

        with patch.object(client, "_get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value.status_code = 200
            # Retorna um dict em vez de list
            mock_client.get.return_value.json.return_value = {"unexpected": "dict"}
            mock_get_client.return_value = mock_client

            with pytest.raises(BackendError) as exc_info:
                client.list_conversations()

        assert "Resposta inesperada do backend" in str(exc_info.value)
        assert "fake-token" not in str(exc_info.value)
