"""Testes do CLI principal."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from labia_chat.cli import (
    auth_me_command,
    chat_command,
    chat_send_command,
    conversations_create_command,
    conversations_list_command,
    main,
    messages_list_command,
    resolve_api_url,
    resolve_token,
)
from labia_chat.cli_client import (
    AuthError,
    CLIClient,
    NotFoundError,
    PermissionError,
)


class TestResolveApiUrl:
    """Testes de resolução de API URL."""

    def test_flag_takes_precedence(self) -> None:
        """Testa que flag tem precedência sobre env e default."""
        with patch.dict("os.environ", {"LABIA_CHAT_API_URL": "http://env.com"}):
            result = resolve_api_url("http://flag.com")
            assert result == "http://flag.com"

    def test_env_used_when_no_flag(self) -> None:
        """Testa que env é usado quando não há flag."""
        with patch.dict("os.environ", {"LABIA_CHAT_API_URL": "http://env.com"}):
            result = resolve_api_url(None)
            assert result == "http://env.com"

    def test_default_used_when_no_flag_no_env(self) -> None:
        """Testa que default é usado quando não há flag nem env."""
        with patch.dict("os.environ", {"LABIA_CHAT_API_URL": ""}, clear=True):
            result = resolve_api_url(None)
            assert result == "http://127.0.0.1:8010"

    def test_trailing_slash_stripped(self) -> None:
        """Testa que trailing slash é removido no CLIClient."""
        client = CLIClient("http://example.com/")
        assert client.api_url == "http://example.com"


class TestResolveToken:
    """Testes de resolução de token."""

    def test_flag_takes_precedence(self) -> None:
        """Testa que flag tem precedência sobre env e prompt."""
        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": "env-token"}):
            with patch("labia_chat.cli.getpass.getpass") as mock_getpass:
                mock_getpass.return_value = "prompt-token"
                result = resolve_token("flag-token")
                assert result == "flag-token"
                mock_getpass.assert_not_called()

    def test_env_used_when_no_flag(self) -> None:
        """Testa que env é usado quando não há flag."""
        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": "env-token"}):
            with patch("labia_chat.cli.getpass.getpass") as mock_getpass:
                result = resolve_token(None)
                assert result == "env-token"
                mock_getpass.assert_not_called()

    def test_prompt_used_when_no_flag_no_env(self) -> None:
        """Testa que prompt é usado quando não há flag nem env."""
        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": ""}, clear=True):
            with patch("labia_chat.cli.getpass.getpass") as mock_getpass:
                mock_getpass.return_value = "prompt-token"
                result = resolve_token(None)
                assert result == "prompt-token"
                mock_getpass.assert_called_once_with("AI-Scope token: ")


class TestChatCommand:
    """Testes do comando chat."""

    def test_chat_command_flow(self) -> None:
        """Testa fluxo completo do chat."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    # Mock validate_token
                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    # Mock create_conversation
                    mock_client.create_conversation.return_value = {
                        "id": "conv-123",
                    }

                    # Mock generate_message
                    mock_client.generate_message.return_value = {
                        "content": "Resposta do assistente",
                    }

                    # Mock input
                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["Hello", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    mock_client.validate_token.assert_called_once()
                    mock_client.create_conversation.assert_called_once()
                    mock_client.generate_message.assert_called_once_with("Hello")
                    mock_client.close.assert_called_once()

    def test_chat_command_auth_error(self) -> None:
        """Testa erro de autenticação."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "invalid-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    from labia_chat.cli_client import AuthError
                    mock_client.validate_token.side_effect = AuthError("Token inválido")

                    result = chat_command(args)

                    assert result == 1
                    mock_client.close.assert_called_once()

class TestMain:
    """Testes da função main."""

    def test_main_with_chat_command(self) -> None:
        """Testa main com comando chat."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("sys.argv", ["labia-chat", "chat"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="chat",
                        api_url=None,
                        token=None,
                        title=None,
                        conversation_id=None,
                        show_last=10,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_chat.assert_called_once_with(args)

    def test_main_without_command(self) -> None:
        """Testa main sem comando."""
        with patch("argparse.ArgumentParser.print_help") as mock_help:
            with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                args = argparse.Namespace(command=None)
                mock_parse.return_value = args

                result = main()

                assert result == 0
                mock_help.assert_called_once()

    def test_main_sys_exit(self) -> None:
        """Testa que main retorna código de saída correto."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 1

            with patch("sys.argv", ["labia-chat", "chat"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="chat",
                        api_url=None,
                        token=None,
                        title=None,
                        conversation_id=None,
                        show_last=10,
                    )
                    mock_parse.return_value = args

                    # main() retorna o código de saída
                    result = main()

                    assert result == 1


class TestChatCommandConversationId:
    """Testes do comando chat com --conversation-id."""

    def test_chat_with_conversation_id(self) -> None:
        """Testa resumo de conversa existente com --conversation-id."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    # Mock validate_token
                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    # Mock get_conversation
                    mock_client.get_conversation.return_value = {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Conversa Retomada",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "archived_at": None,
                    }

                    # Mock list_messages
                    mock_client.list_messages.return_value = [
                        {
                            "id": "msg-1",
                            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "role": "user",
                            "content": "Olá!",
                            "sequence_index": 0,
                            "model": None,
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:00Z",
                        },
                        {
                            "id": "msg-2",
                            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "role": "assistant",
                            "content": "Olá! Como posso ajudar?",
                            "sequence_index": 1,
                            "model": "qwen-coder-next",
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:01Z",
                        },
                    ]

                    # Mock generate_message
                    mock_client.generate_message.return_value = {
                        "content": "Resposta do assistente",
                    }

                    # Mock input
                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["Continuação", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    mock_client.validate_token.assert_called_once()
                    mock_client.get_conversation.assert_called_once_with(
                        "123e4567-e89b-12d3-a456-426614174000"
                    )
                    mock_client.list_messages.assert_called_once_with(
                        "123e4567-e89b-12d3-a456-426614174000"
                    )
                    mock_client.generate_message.assert_called_once_with("Continuação")
                    mock_client.close.assert_called_once()

    def test_chat_with_conversation_id_and_show_last(self) -> None:
        """Testa resumo de conversa com --show-last 2."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=2,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.get_conversation.return_value = {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Conversa",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "archived_at": None,
                    }

                    mock_client.list_messages.return_value = [
                        {
                            "id": f"msg-{i}",
                            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "role": "user" if i % 2 == 0 else "assistant",
                            "content": f"Mensagem {i}",
                            "sequence_index": i,
                            "model": None,
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:00Z",
                        }
                        for i in range(5)
                    ]

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["Nova", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    mock_client.list_messages.assert_called_once_with(
                        "123e4567-e89b-12d3-a456-426614174000"
                    )

    def test_chat_with_conversation_id_show_last_zero(self) -> None:
        """Testa resumo de conversa com --show-last 0 (não exibe histórico)."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=0,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.get_conversation.return_value = {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Conversa",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "archived_at": None,
                    }

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["Nova", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    # list_messages não deve ser chamado quando show_last=0
                    mock_client.list_messages.assert_not_called()

    def test_chat_with_conversation_id_404(self) -> None:
        """Testa resumo de conversa não encontrada (404)."""
        from labia_chat.cli_client import NotFoundError

        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.get_conversation.side_effect = NotFoundError(
                        "Conversa não encontrada"
                    )

                    result = chat_command(args)

                    assert result == 1
                    mock_client.close.assert_called_once()


class TestHistoryCommand:
    """Testes do comando /history."""

    def test_history_command_success(self) -> None:
        """Testa comando /history bem-sucedido."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.get_conversation.return_value = {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Conversa",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "archived_at": None,
                    }

                    mock_client.list_messages.return_value = [
                        {
                            "id": "msg-1",
                            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "role": "user",
                            "content": "Olá!",
                            "sequence_index": 0,
                            "model": None,
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:00Z",
                        },
                        {
                            "id": "msg-2",
                            "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                            "role": "assistant",
                            "content": "Olá! Como posso ajudar?",
                            "sequence_index": 1,
                            "model": "qwen-coder-next",
                            "metadata": {},
                            "created_at": "2024-01-01T00:00:01Z",
                        },
                    ]

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["/history", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    # list_messages deve ser chamado duas vezes:
                    # uma vez no início e outra vez no /history
                    assert mock_client.list_messages.call_count == 2

    def test_history_command_error(self) -> None:
        """Testa comando /history com erro no backend."""
        from labia_chat.cli_client import BackendError

        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.get_conversation.return_value = {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "Conversa",
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "archived_at": None,
                    }

                    # Erro no /history
                    mock_client.list_messages.side_effect = BackendError(
                        "Erro no backend"
                    )

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["/history", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    # O erro é tratado e o loop continua
                    assert mock_client.list_messages.call_count == 2

    def test_preserve_new_conversation_flow(self) -> None:
        """Testa que nova conversa é criada quando não há --conversation-id."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.create_conversation.return_value = {
                        "id": "conv-nova",
                    }

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["Nova", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    mock_client.create_conversation.assert_called_once()
                    mock_client.get_conversation.assert_not_called()

    def test_preserve_help_and_exit(self) -> None:
        """Testa que /help e /exit continuam funcionando."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }

                    mock_client.create_conversation.return_value = {
                        "id": "conv-nova",
                    }

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    with patch("labia_chat.cli.input") as mock_input:
                        mock_input.side_effect = ["/help", "/exit"]

                        result = chat_command(args)

                    assert result == 0
                    mock_client.generate_message.assert_not_called()


class TestChatCommandShowLastValidation:
    """Testes de validação de --show-last."""

    def test_negative_show_last(self) -> None:
        """Testa que --show-last negativo é rejeitado."""
        from labia_chat.cli import main

        with patch("sys.argv", ["labia-chat", "chat", "--show-last", "-5"]):
            result = main()

            assert result == 1


class TestAuthMeCommand:
    """Testes do comando 'auth me'."""

    def test_auth_me_success(self) -> None:
        """Testa 'auth me' com sucesso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.return_value = {
                "id": "user123",
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False,
                "roles": ["public", "chat_vllm"],
            }

            result = auth_me_command(args)

            assert result == 0
            mock_client.set_token.assert_called_once_with("test-token")
            mock_client.validate_token.assert_called_once()
            mock_client.close.assert_called_once()

    def test_auth_me_with_env_token(self) -> None:
        """Testa 'auth me' usando token do env."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token=None,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "env-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "id": "user123",
                        "username": "testuser",
                        "email": "test@example.com",
                        "is_active": True,
                    }

                    result = auth_me_command(args)

                    assert result == 0
                    mock_client.set_token.assert_called_once_with("env-token")

    def test_auth_me_auth_error(self) -> None:
        """Testa 'auth me' com token inválido."""
        from labia_chat.cli_client import AuthError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="invalid-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = AuthError("Token inválido")

            result = auth_me_command(args)

            assert result == 1
            mock_client.close.assert_called_once()

    def test_auth_me_permission_error(self) -> None:
        """Testa 'auth me' sem permissão."""
        from labia_chat.cli_client import PermissionError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="no-permission-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = PermissionError(
                "sem permissão chat_vllm"
            )

            result = auth_me_command(args)

            assert result == 1

    def test_auth_me_backend_error(self) -> None:
        """Testa 'auth me' com erro no backend."""
        from labia_chat.cli_client import BackendError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = BackendError(
                "Backend indisponível"
            )

            result = auth_me_command(args)

            assert result == 1


class TestConversationsCreateCommand:
    """Testes do comando 'conversations create'."""

    def test_conversations_create_success_with_title(self) -> None:
        """Testa 'conversations create' com título."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            title="Teste",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.create_conversation.return_value = {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Teste",
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "archived_at": None,
            }

            result = conversations_create_command(args)

            assert result == 0
            mock_client.set_token.assert_called_once_with("test-token")
            mock_client.create_conversation.assert_called_once_with(title="Teste")
            mock_client.close.assert_called_once()

    def test_conversations_create_success_without_title(self) -> None:
        """Testa 'conversations create' sem título."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            title=None,
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.create_conversation.return_value = {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": None,
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "archived_at": None,
            }

            result = conversations_create_command(args)

            assert result == 0
            mock_client.create_conversation.assert_called_once_with(title=None)

    def test_conversations_create_auth_error(self) -> None:
        """Testa 'conversations create' com token inválido."""
        from labia_chat.cli_client import AuthError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="invalid-token",
            title="Teste",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.create_conversation.side_effect = AuthError("Token inválido")

            result = conversations_create_command(args)

            assert result == 1
            mock_client.close.assert_called_once()


class TestChatSendCommand:
    """Testes do comando 'chat send'."""

    def test_chat_send_success(self) -> None:
        """Testa 'chat send' com sucesso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá, mundo!",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.return_value = {
                "id": "user123",
                "username": "testuser",
            }

            mock_client.generate_message.return_value = {
                "id": "msg-123",
                "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                "role": "assistant",
                "content": "Esta é uma resposta de teste.",
                "sequence_index": 1,
                "model": "qwen-coder-next",
                "metadata": {},
                "created_at": "2024-01-01T00:00:00Z",
            }

            result = chat_send_command(args)

            assert result == 0
            mock_client.set_token.assert_called_once_with("test-token")
            mock_client.validate_token.assert_called_once()
            mock_client.generate_message.assert_called_once_with("Olá, mundo!")
            mock_client.close.assert_called_once()

    def test_chat_send_with_env_token(self) -> None:
        """Testa 'chat send' usando token do env."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá!",
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch("labia_chat.cli.resolve_token") as mock_resolve_token:
                mock_resolve_token.return_value = "env-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.return_value = {
                        "id": "user123",
                        "username": "testuser",
                    }

                    mock_client.generate_message.return_value = {
                        "content": "Resposta",
                    }

                    result = chat_send_command(args)

                    assert result == 0
                    mock_client.set_token.assert_called_once_with("env-token")

    def test_chat_send_auth_error(self) -> None:
        """Testa 'chat send' com token inválido."""
        from labia_chat.cli_client import AuthError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="invalid-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá!",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = AuthError("Token inválido")

            result = chat_send_command(args)

            assert result == 1
            mock_client.close.assert_called_once()

    def test_chat_send_not_found_error(self) -> None:
        """Testa 'chat send' com conversa não encontrada."""
        from labia_chat.cli_client import NotFoundError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="nonexistent",
            message="Olá!",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.return_value = {
                "id": "user123",
                "username": "testuser",
            }

            mock_client.generate_message.side_effect = NotFoundError(
                "Conversa não encontrada"
            )

            result = chat_send_command(args)

            assert result == 1

    def test_chat_send_backend_error(self) -> None:
        """Testa 'chat send' com erro no backend."""
        from labia_chat.cli_client import BackendError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá!",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.return_value = {
                "id": "user123",
                "username": "testuser",
            }

            mock_client.generate_message.side_effect = BackendError(
                "Erro no backend"
            )

            result = chat_send_command(args)

            assert result == 1


class TestConversationsListCommand:
    """Testes do comando 'conversations list'."""

    def test_conversations_list_success(self) -> None:
        """Testa 'conversations list' com sucesso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_conversations.return_value = [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Conversa 1",
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T10:00:00Z",
                    "archived_at": None,
                },
                {
                    "id": "890abc12-def3-4567-8901-234567890abc",
                    "title": "Conversa 2",
                    "created_at": "2024-01-02T11:00:00Z",
                    "updated_at": "2024-01-02T11:00:00Z",
                    "archived_at": None,
                },
            ]

            result = conversations_list_command(args)

            assert result == 0
            mock_client.list_conversations.assert_called_once()

    def test_conversations_list_empty(self) -> None:
        """Testa 'conversations list' sem conversas."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_conversations.return_value = []

            result = conversations_list_command(args)

            assert result == 0

    def test_conversations_list_auth_error(self) -> None:
        """Testa 'conversations list' com erro de autenticação."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="invalid-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_conversations.side_effect = AuthError(
                "Token inválido ou expirado"
            )

            result = conversations_list_command(args)

            assert result == 1

    def test_conversations_list_permission_error(self) -> None:
        """Testa 'conversations list' com erro de permissão."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="no-permission-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_conversations.side_effect = PermissionError(
                "Sem permissão chat_vllm"
            )

            result = conversations_list_command(args)

            assert result == 1


class TestMessagesListCommand:
    """Testes do comando 'messages list'."""

    def test_messages_list_success(self) -> None:
        """Testa 'messages list' com sucesso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_messages.return_value = [
                {
                    "id": "msg-1",
                    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                    "role": "user",
                    "content": "Olá!",
                    "sequence_index": 0,
                    "model": None,
                    "metadata": {},
                    "created_at": "2024-01-01T10:00:00Z",
                },
                {
                    "id": "msg-2",
                    "conversation_id": "123e4567-e89b-12d3-a456-426614174000",
                    "role": "assistant",
                    "content": "Olá! Como posso ajudar?",
                    "sequence_index": 1,
                    "model": "qwen-coder-next",
                    "metadata": {},
                    "created_at": "2024-01-01T10:00:01Z",
                },
            ]

            result = messages_list_command(args)

            assert result == 0
            mock_client.list_messages.assert_called_once_with(
                "123e4567-e89b-12d3-a456-426614174000"
            )

    def test_messages_list_empty(self) -> None:
        """Testa 'messages list' sem mensagens."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_messages.return_value = []

            result = messages_list_command(args)

            assert result == 0

    def test_messages_list_not_found_error(self) -> None:
        """Testa 'messages list' com conversa não encontrada."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="nonexistent",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.list_messages.side_effect = NotFoundError(
                "Conversa não encontrada"
            )

            result = messages_list_command(args)

            assert result == 1

    def test_messages_list_missing_conversation_id(self) -> None:
        """Testa 'messages list' sem conversation_id."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id=None,
        )

        # Simula o comportamento do argparse que exige conversation_id
        # O argparse já valida isso antes de chamar o command
        result = messages_list_command(args)

        # Como o argparse já validou, este teste garante que o command
        # não quebra com None, mas o argparse já impede isso
        assert result == 1


class TestMainSmokeCommands:
    """Testes da função main."""

    def test_main_auth_me_command(self) -> None:
        """Testa main com comando 'auth me'."""
        with patch("labia_chat.cli.auth_me_command") as mock_auth:
            mock_auth.return_value = 0

            with patch("sys.argv", ["labia-chat", "auth", "me"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="auth",
                        auth_command="me",
                        api_url=None,
                        token=None,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_auth.assert_called_once_with(args)

    def test_main_conversations_create_command(self) -> None:
        """Testa main com comando 'conversations create'."""
        with patch("labia_chat.cli.conversations_create_command") as mock_create:
            mock_create.return_value = 0

            with patch("sys.argv", ["labia-chat", "conversations", "create"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="conversations",
                        conversations_command="create",
                        api_url=None,
                        token=None,
                        title=None,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_create.assert_called_once_with(args)

    def test_main_conversations_list_command(self) -> None:
        """Testa main com comando 'conversations list'."""
        with patch("labia_chat.cli.conversations_list_command") as mock_list:
            mock_list.return_value = 0

            with patch("sys.argv", ["labia-chat", "conversations", "list"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="conversations",
                        conversations_command="list",
                        api_url=None,
                        token=None,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_list.assert_called_once_with(args)

    def test_main_messages_list_command(self) -> None:
        """Testa main com comando 'messages list'."""
        with patch("labia_chat.cli.messages_list_command") as mock_list:
            mock_list.return_value = 0

            with patch("sys.argv", ["labia-chat", "messages", "list", "conv-id"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="messages",
                        messages_command="list",
                        conversation_id="conv-id",
                        api_url=None,
                        token=None,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_list.assert_called_once_with(args)

    def test_main_chat_send_command(self) -> None:
        """Testa main com comando 'chat send'."""
        with patch("labia_chat.cli.chat_send_command") as mock_send:
            mock_send.return_value = 0

            with patch("sys.argv", ["labia-chat", "chat", "send", "conv-id", "msg"]):
                with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                    args = argparse.Namespace(
                        command="chat",
                        chat_command="send",
                        conversation_id="conv-id",
                        message="msg",
                        api_url=None,
                        token=None,
                    )
                    mock_parse.return_value = args

                    result = main()

                    assert result == 0
                    mock_send.assert_called_once_with(args)

    def test_main_chat_send_missing_conversation_id(self) -> None:
        """Testa 'chat send' sem conversation_id (argparse sai com código 2)."""
        with patch("sys.argv", ["labia-chat", "chat", "send"]):
            # argparse sai com código 2 quando argumentos obrigatórios faltam
            # SystemExit(2) é levantado, main() captura e retorna 1
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2

    def test_main_chat_send_missing_message(self) -> None:
        """Testa 'chat send' sem message (argparse sai com código 2)."""
        with patch("sys.argv", ["labia-chat", "chat", "send", "conv-id"]):
            # argparse sai com código 2 quando argumentos obrigatórios faltam
            # SystemExit(2) é levantado, main() captura e retorna 1
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 2
