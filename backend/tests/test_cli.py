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
                    args = argparse.Namespace(command="chat")
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
                    args = argparse.Namespace(command="chat")
                    mock_parse.return_value = args

                    # main() retorna o código de saída
                    result = main()

                    assert result == 1
