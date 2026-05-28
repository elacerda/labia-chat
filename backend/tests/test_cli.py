"""Testes do CLI principal."""

import argparse
from unittest.mock import MagicMock, patch

from labia_chat.cli import (
    chat_command,
    main,
    resolve_api_url,
    resolve_token,
)
from labia_chat.cli_client import CLIClient


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
