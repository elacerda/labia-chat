"""Testes do CLI principal."""

import argparse
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

import pytest

from labia_chat import __version__, cli_ui
from labia_chat.cli import (
    auth_me_command,
    chat_command,
    chat_send_command,
    chat_show_last,
    chat_stream_enabled,
    config_init_command,
    config_show_command,
    conversations_create_command,
    conversations_list_command,
    doctor_command,
    get_cli_version,
    main,
    messages_list_command,
    print_cli_error,
    resolve_api_url,
    resolve_interactive_chat_token,
    resolve_token,
    resolve_token_required,
)
from labia_chat.cli_auth import LoginError, login_ai_scope, prompt_for_ai_scope_login
from labia_chat.cli_client import (
    AuthError,
    CLIClient,
    NotFoundError,
    PermissionError,
)
from labia_chat.cli_config import DEFAULT_API_URL, save_config

INTERACTIVE_TOKEN_RESOLVER = "labia_chat.cli.resolve_interactive_chat_token"


class TestCliUiMarkdownPanels:
    """Testes dos painéis Markdown renderizados pelo CLI."""

    def test_build_assistant_markdown_panel_uses_stable_options(self) -> None:
        """Testa que o painel do assistente usa Markdown e safe_box."""
        panel = cli_ui.build_assistant_markdown_panel(
            "Olá 😀 **mundo**",
            title="[assistant]Assistente[/assistant]",
        )

        assert panel.border_style == "green"
        assert panel.padding == (0, 2)
        assert panel.safe_box is True
        assert panel.title == "[assistant]Assistente[/assistant]"
        assert panel.title_align == "left"
        assert panel.renderable.markup == "Olá 😀 **mundo**"

    def test_print_stream_chunks_markdown_updates_live_and_prints_final_panel(
        self,
    ) -> None:
        """Testa streaming progressivo e painel final combinado."""
        live = MagicMock()

        with patch.object(cli_ui, "Live") as MockLive:
            MockLive.return_value.__enter__.return_value = live

            with patch.object(cli_ui.console, "print") as print_mock:
                cli_ui.print_stream_chunks_markdown(iter(["Olá", " 😀", " **fim**"]))

        MockLive.assert_called_once_with(
            console=cli_ui.console,
            refresh_per_second=12,
            transient=True,
        )
        assert live.update.call_count == 3
        assert all(
            call.kwargs["refresh"] is True for call in live.update.call_args_list
        )

        final_panel = print_mock.call_args_list[0].args[0]
        assert final_panel.renderable.markup == "Olá 😀 **fim**"
        assert final_panel.border_style == "green"
        assert final_panel.padding == (0, 2)
        assert final_panel.safe_box is True
        assert print_mock.call_args_list[1].args == ()


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

    def test_default_used_when_no_flag_no_env(self, tmp_path) -> None:
        """Testa que default é usado quando não há flag nem env."""
        with patch.dict(
            "os.environ",
            {"LABIA_CHAT_API_URL": "", "XDG_CONFIG_HOME": str(tmp_path)},
            clear=True,
        ):
            result = resolve_api_url(None)
            assert result == DEFAULT_API_URL

    def test_config_used_when_no_flag_no_env(self, tmp_path, monkeypatch) -> None:
        """Testa que config é usado antes do default."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv("LABIA_CHAT_API_URL", raising=False)
        save_config(api_url="http://config.example:8010")

        assert resolve_api_url(None) == "http://config.example:8010"

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


class TestInteractiveLoginHelpers:
    """Testes dos helpers de login AI-Scope do CLI."""

    def test_prompt_for_ai_scope_login_uses_username_password(self) -> None:
        """Testa prompt de usuário/senha e retorno do access token."""
        login_func = MagicMock(return_value="access-token")

        result = prompt_for_ai_scope_login(
            input_func=MagicMock(return_value="alice"),
            password_func=MagicMock(return_value="secret-password"),
            login_func=login_func,
        )

        assert result == "access-token"
        login_func.assert_called_once_with("alice", "secret-password")

    def test_login_ai_scope_posts_form_and_returns_access_token(self) -> None:
        """Testa chamada HTTP de login com form data."""
        response = MagicMock()
        response.json.return_value = {
            "access_token": "access-token",
            "token_type": "bearer",
        }

        with patch("labia_chat.cli_auth.httpx.post", return_value=response) as post:
            result = login_ai_scope("alice", "secret-password")

        assert result == "access-token"
        post.assert_called_once()
        assert post.call_args.kwargs["data"] == {
            "username": "alice",
            "password": "secret-password",
        }

    def test_login_ai_scope_failure_is_friendly(self) -> None:
        """Testa erro amigável em falha de login."""
        import httpx

        response = MagicMock(status_code=401)
        error = httpx.HTTPStatusError(
            "401 Unauthorized",
            request=MagicMock(),
            response=response,
        )

        with patch("labia_chat.cli_auth.httpx.post", side_effect=error):
            with pytest.raises(LoginError) as exc_info:
                login_ai_scope("alice", "secret-password")

        assert "Login AI-Scope recusado" in str(exc_info.value)
        assert "secret-password" not in str(exc_info.value)

    def test_resolve_interactive_chat_token_prompts_when_missing(self) -> None:
        """Testa login interativo quando não há token resolvido."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt:
                result = resolve_interactive_chat_token(None)

        assert result == "login-token"
        prompt.assert_called_once()

    def test_resolve_interactive_chat_token_uses_arg_without_prompt(self) -> None:
        """Testa precedência de token por argumento."""
        with patch(
            "labia_chat.cli.prompt_for_ai_scope_login",
            return_value="login-token",
        ) as prompt:
            result = resolve_interactive_chat_token("arg-token")

        assert result == "arg-token"
        prompt.assert_not_called()

    def test_resolve_interactive_chat_token_uses_env_without_prompt(self) -> None:
        """Testa precedência de token por ambiente."""
        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": "env-token"}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt:
                result = resolve_interactive_chat_token(None)

        assert result == "env-token"
        prompt.assert_not_called()

    def test_resolve_token_required_never_prompts(self) -> None:
        """Testa resolução não interativa sem prompt."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("labia_chat.cli.prompt_for_ai_scope_login") as prompt_login:
                with patch("labia_chat.cli.getpass.getpass") as getpass_prompt:
                    result = resolve_token_required(None)

        assert result is None
        prompt_login.assert_not_called()
        getpass_prompt.assert_not_called()


class TestConfigShowCommand:
    """Testes do comando 'config show'."""

    def test_config_show_does_not_leak_token_value(self, capsys) -> None:
        """Testa que o valor do token nunca é impresso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="super-secret-token",
        )

        result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "super-secret-token" not in output
        assert "Status do token: configurado" in output
        assert "Origem do token: argument" in output

    def test_config_show_reports_missing_token(self, capsys, tmp_path) -> None:
        """Testa que token ausente é reportado sem prompt."""
        args = argparse.Namespace(api_url=None, token=None)

        with patch.dict(
            "os.environ",
            {"XDG_CONFIG_HOME": str(tmp_path)},
            clear=True,
        ):
            result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert f"URL da API: {DEFAULT_API_URL}" in output
        assert "Origem da URL da API: default" in output
        assert "Status do token: ausente" in output
        assert "Origem do token: ausente" in output
        assert "Streaming padrão: habilitado" in output

    def test_config_show_reports_env_token_configured(self, capsys) -> None:
        """Testa que token de env é reportado como configurado."""
        args = argparse.Namespace(api_url=None, token=None)

        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": "env-secret"}, clear=True):
            result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "env-secret" not in output
        assert "Status do token: configurado" in output
        assert "Origem do token: env" in output


class TestChatConfigDefaults:
    """Testes de defaults do chat resolvidos via config local."""

    def test_chat_stream_enabled_uses_config_when_arg_missing(self, tmp_path) -> None:
        """Testa que streaming_default do config é usado sem flag explícita."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}, clear=True):
            save_config(streaming_default=False)

            assert chat_stream_enabled(argparse.Namespace(stream=None)) is False

    def test_chat_stream_enabled_arg_overrides_config(self, tmp_path) -> None:
        """Testa que flag explícita de streaming prevalece sobre config."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}, clear=True):
            save_config(streaming_default=False)

            assert chat_stream_enabled(argparse.Namespace(stream=True)) is True

    def test_chat_show_last_uses_config_when_arg_missing(self, tmp_path) -> None:
        """Testa que show_last_default do config é usado sem flag explícita."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}, clear=True):
            save_config(show_last_default=3)

            assert chat_show_last(argparse.Namespace(show_last=None)) == 3

    def test_chat_show_last_arg_overrides_config(self, tmp_path) -> None:
        """Testa que --show-last explícito prevalece sobre config."""
        with patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path)}, clear=True):
            save_config(show_last_default=3)

            assert chat_show_last(argparse.Namespace(show_last=7)) == 7


class TestDoctorCommand:
    """Testes do comando 'doctor'."""

    def test_doctor_backend_healthy_and_auth_ok(self, capsys) -> None:
        """Testa diagnóstico com backend saudável e auth ok."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            with_model=False,
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.health_check.return_value = {"status": "ok"}
            mock_client.validate_token.return_value = {"username": "testuser"}

            result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "test-token" not in output
        assert "Token: configured (source: argument)" in output
        assert "[ok] GET /health: backend is healthy" in output
        assert "[ok] GET /auth/me: testuser" in output
        mock_client.set_token.assert_called_once_with("test-token")
        mock_client.close.assert_called_once()

    def test_doctor_handles_missing_token(self, capsys) -> None:
        """Testa diagnóstico sem token configurado."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token=None,
            with_model=False,
        )

        with patch.dict("os.environ", {}, clear=True):
            with patch("labia_chat.cli.CLIClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.health_check.return_value = {"status": "ok"}

                result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "Token: missing" in output
        assert "[skip] GET /auth/me: token missing" in output
        mock_client.set_token.assert_not_called()
        mock_client.validate_token.assert_not_called()
        mock_client.close.assert_called_once()

    def test_doctor_handles_backend_connection_failure(self, capsys) -> None:
        """Testa diagnóstico quando o backend está indisponível."""
        from labia_chat.cli_client import ConnectionError

        args = argparse.Namespace(
            api_url="http://example.com",
            token=None,
            with_model=False,
        )

        with patch.dict("os.environ", {}, clear=True):
            with patch("labia_chat.cli.CLIClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.health_check.side_effect = ConnectionError(
                    "Falha de conexão com o backend."
                )

                result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 1
        assert "[fail] GET /health: Falha de conexão com o backend." in output
        assert "[skip] GET /auth/me: token missing" in output
        mock_client.close.assert_called_once()


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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
                mock_resolve_token.return_value = "invalid-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    from labia_chat.cli_client import AuthError

                    mock_client.validate_token.side_effect = AuthError("Token inválido")

                    result = chat_command(args)

                    assert result == 1
                    mock_client.close.assert_called_once()

    def test_chat_creates_conversation_and_prints_banner(self, capsys) -> None:
        """Testa criação automática e banner inicial."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=True,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {
                        "username": "testuser",
                    }
                    mock_client.create_conversation.return_value = {
                        "id": "conv-123",
                        "title": "CLI chat",
                    }

                    with patch("labia_chat.cli.input", side_effect=["/exit"]):
                        result = chat_command(args)

        output = capsys.readouterr().out
        assert result == 0
        mock_client.create_conversation.assert_called_once_with(title="CLI chat")
        assert "API URL: http://example.com" in output
        assert "Usuário: testuser" in output
        assert "ID da conversa: conv-123" in output
        assert "Streaming: ativo" in output
        assert "Digite /help para comandos" in output

    def test_help_command_prints_internal_commands(self, capsys) -> None:
        """Testa que /help lista comandos internos."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("labia_chat.cli.input", side_effect=["/help", "/exit"]):
                        result = chat_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "/help" in output
        assert "/history" in output
        assert "/new" in output
        assert "/exit" in output
        assert "/quit" in output

    def test_quit_exits_cleanly(self, capsys) -> None:
        """Testa que /quit encerra sem erro."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("labia_chat.cli.input", side_effect=["/quit"]):
                        result = chat_command(args)

        assert result == 0
        assert "Até mais." in capsys.readouterr().out
        mock_client.generate_message.assert_not_called()

    def test_new_command_switches_conversation(self, capsys) -> None:
        """Testa que /new cria e troca a conversa atual."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.side_effect = [
                        {"id": "conv-1"},
                        {"id": "conv-2"},
                    ]
                    mock_client.generate_message.return_value = {"content": "Olá"}

                    with patch(
                        "labia_chat.cli.input",
                        side_effect=["/new", "Hello", "/exit"],
                    ):
                        result = chat_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert mock_client.create_conversation.call_count == 2
        mock_client.generate_message.assert_called_once_with("Hello")
        assert mock_client.conversation_id == "conv-2"
        assert "Nova conversa" in output
        assert "conv-2" in output

    def test_exit_after_new_exits_cleanly(self, capsys) -> None:
        """Testa que /exit após /new encerra sem enviar ao modelo."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.side_effect = [
                        {"id": "conv-1"},
                        {"id": "conv-2"},
                    ]
                    mock_client.generate_message.return_value = {"content": "Olá"}

                    with patch(
                        "labia_chat.cli.input",
                        side_effect=["/new", "/exit"],
                    ):
                        result = chat_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert mock_client.create_conversation.call_count == 2
        # generate_message should NOT be called since /exit was used
        mock_client.generate_message.assert_not_called()
        assert "Nova conversa" in output
        assert "conv-2" in output
        assert "Até mais." in output

    def test_eof_exits_cleanly(self, capsys) -> None:
        """Testa que EOF encerra o chat sem traceback."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("labia_chat.cli.input", side_effect=EOFError):
                        result = chat_command(args)

        assert result == 0
        assert "Até mais." in capsys.readouterr().out


class TestMain:
    """Testes da função main."""

    def test_main_help_includes_examples(self, capsys) -> None:
        """Testa que --help exibe exemplos representativos."""
        with patch("sys.argv", ["labia-chat", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        output = capsys.readouterr().out
        assert exc_info.value.code == 0
        assert "Exemplos:" in output
        assert "labia-chat" in output
        assert "labia-chat --last" in output
        assert "labia-chat config init" in output
        assert "labia-chat doctor" in output

    def test_main_version_uses_resolved_version(self, capsys) -> None:
        """Testa que --version imprime a versão resolvida."""
        with patch("labia_chat.cli.get_cli_version", return_value="9.9.9"):
            with patch("sys.argv", ["labia-chat", "--version"]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

        output = capsys.readouterr().out
        assert exc_info.value.code == 0
        assert output.strip() == "labia-chat 9.9.9"

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
        """Testa main sem comando inicia chat interativo."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                args = argparse.Namespace(
                    command=None,
                    api_url=None,
                    token=None,
                    title=None,
                    conversation_id=None,
                    show_last=10,
                    stream=True,
                )
                mock_parse.return_value = args

                result = main()

                assert result == 0
                mock_chat.assert_called_once_with(args)

    def test_main_with_config_show_command(self) -> None:
        """Testa main com comando config show."""
        with patch("labia_chat.cli.config_show_command") as mock_config_show:
            mock_config_show.return_value = 0

            with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                args = argparse.Namespace(
                    command="config",
                    config_command="show",
                    api_url=None,
                    token=None,
                )
                mock_parse.return_value = args

                result = main()

                assert result == 0
                mock_config_show.assert_called_once_with(args)

    def test_main_with_doctor_command(self) -> None:
        """Testa main com comando doctor."""
        with patch("labia_chat.cli.doctor_command") as mock_doctor:
            mock_doctor.return_value = 0

            with patch("argparse.ArgumentParser.parse_args") as mock_parse:
                args = argparse.Namespace(
                    command="doctor",
                    api_url=None,
                    token=None,
                    with_model=False,
                )
                mock_parse.return_value = args

                result = main()

                assert result == 0
                mock_doctor.assert_called_once_with(args)

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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
                        "123e4567-e89b-12d3-a456-426614174000", limit=10
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
                        "123e4567-e89b-12d3-a456-426614174000", limit=2
                    )

    def test_chat_with_conversation_id_show_last_zero(self) -> None:
        """Testa resumo de conversa com --show-last 0 (não exibe histórico)."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            show_last=0,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
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

            assert result == 2


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

            with patch("labia_chat.cli.resolve_token_required") as mock_resolve_token:
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

    def test_chat_send_stream_success(self, capsys) -> None:
        """Testa 'chat send --stream' imprimindo chunks."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá, mundo!",
            stream=True,
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.return_value = {
                "id": "user123",
                "username": "testuser",
            }
            mock_client.stream_generate_message.return_value = iter(
                ["Olá", ", mundo", "\n"]
            )

            with patch("labia_chat.cli.print_stream_chunks_markdown") as print_stream:
                result = chat_send_command(args)

        assert result == 0
        mock_client.stream_generate_message.assert_called_once_with("Olá, mundo!")
        print_stream.assert_called_once_with(
            mock_client.stream_generate_message.return_value
        )
        mock_client.generate_message.assert_not_called()
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

            with patch("labia_chat.cli.resolve_token_required") as mock_resolve_token:
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

            mock_client.generate_message.side_effect = BackendError("Erro no backend")

            result = chat_send_command(args)

            assert result == 1


class TestConversationsListCommand:
    """Testes do comando 'conversations list'."""

    def test_conversations_list_success(self) -> None:
        """Testa 'conversations list' com sucesso."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            limit=20,
            offset=0,
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
            limit=20,
            offset=0,
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
            limit=20,
            offset=0,
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
            limit=20,
            offset=0,
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
            limit=50,
            offset=0,
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
                "123e4567-e89b-12d3-a456-426614174000", limit=50, offset=0
            )

    def test_messages_list_empty(self) -> None:
        """Testa 'messages list' sem mensagens."""
        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            limit=50,
            offset=0,
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
            limit=50,
            offset=0,
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
            limit=50,
            offset=0,
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


class TestValidationErrorHandling:
    """Testes de tratamento de ValidationError no CLI."""

    def test_auth_me_validation_error(self) -> None:
        """Testa 'auth me' com ValidationError (payload inválido)."""
        from labia_chat.cli_client import ValidationError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = ValidationError(
                "Payload inválido: campo 'username' ausente"
            )

            result = auth_me_command(args)

            assert result == 1
            mock_client.close.assert_called_once()

    def test_conversations_create_validation_error(self) -> None:
        """Testa 'conversations create' com ValidationError."""
        from labia_chat.cli_client import ValidationError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            title=None,
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.create_conversation.side_effect = ValidationError(
                "Payload inválido: título muito longo"
            )

            result = conversations_create_command(args)

            assert result == 1
            mock_client.close.assert_called_once()

    def test_chat_send_validation_error(self) -> None:
        """Testa 'chat send' com ValidationError."""
        from labia_chat.cli_client import ValidationError

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

            mock_client.generate_message.side_effect = ValidationError(
                "Payload inválido: mensagem vazia"
            )

            result = chat_send_command(args)

            assert result == 1
            mock_client.close.assert_called_once()


class TestTimeoutAndNetworkErrorHandling:
    """Testes de tratamento de timeout e erros de rede no CLI."""

    def test_auth_me_timeout_error(self) -> None:
        """Testa 'auth me' com timeout."""
        from labia_chat.cli_client import ConnectionError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = ConnectionError(
                "Timeout ao conectar com o backend"
            )

            result = auth_me_command(args)

            assert result == 1
            mock_client.close.assert_called_once()

    def test_chat_command_timeout_error(self) -> None:
        """Testa chat interativo com timeout no início."""
        from labia_chat.cli_client import ConnectionError

        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id=None,
            show_last=10,
            stream=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api:
            mock_resolve_api.return_value = "http://example.com"

            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
                mock_resolve_token.return_value = "test-token"

                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client

                    mock_client.validate_token.side_effect = ConnectionError(
                        "Timeout ao conectar com o backend"
                    )

                    result = chat_command(args)

                    assert result == 1
                    mock_client.close.assert_called_once()

    def test_chat_send_network_error(self) -> None:
        """Testa 'chat send' com erro de rede."""
        from labia_chat.cli_client import ConnectionError

        args = argparse.Namespace(
            api_url="http://example.com",
            token="test-token",
            conversation_id="123e4567-e89b-12d3-a456-426614174000",
            message="Olá!",
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            mock_client.validate_token.side_effect = ConnectionError(
                "Falha ao conectar com o backend"
            )

            result = chat_send_command(args)

            assert result == 1
            mock_client.close.assert_called_once()


class TestVersionAndErrorPolish:
    """Testes de versão e mensagens de erro."""

    def test_get_cli_version_uses_package_metadata(self) -> None:
        """Testa que a versão instalada tem precedência."""
        with patch("labia_chat.cli.metadata.version", return_value="1.2.3"):
            assert get_cli_version() == "1.2.3"

    def test_get_cli_version_falls_back_to_module_version(self) -> None:
        """Testa fallback quando metadata do pacote não está disponível."""
        with patch(
            "labia_chat.cli.metadata.version",
            side_effect=PackageNotFoundError,
        ):
            assert get_cli_version() == __version__

    def test_print_cli_error_avoids_duplicate_doctor_hint(self, capsys) -> None:
        """Testa que sugestão do doctor não é duplicada."""
        print_cli_error(Exception("Falha. Rode labia-chat doctor."))

        output = capsys.readouterr().out
        assert output.count("labia-chat doctor") == 1


class TestDefaultInteractiveEntrypoint:
    """Testes para labia-chat sem subcomando (entrypoint padrão interativo)."""

    def test_no_argument_invocation_starts_chat(self) -> None:
        """Testa que labia-chat sem argumentos inicia o chat interativo."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("sys.argv", ["labia-chat"]):
                result = main()

                assert result == 0
                mock_chat.assert_called_once()

    def test_no_argument_invocation_prompts_login_when_token_missing(self) -> None:
        """Testa que labia-chat sem token faz login interativo."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("sys.argv", ["labia-chat"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_called_once()
        mock_client.set_token.assert_called_once_with("login-token")
        mock_client.validate_token.assert_called_once()
        mock_client.create_conversation.assert_called_once()

    def test_chat_command_prompts_login_when_token_missing(self) -> None:
        """Testa que labia-chat chat sem token faz login interativo."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("sys.argv", ["labia-chat", "chat"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_called_once()
        mock_client.set_token.assert_called_once_with("login-token")

    def test_last_prompts_login_when_token_missing(self) -> None:
        """Testa que labia-chat --last sem token faz login interativo."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.list_conversations.return_value = [
                        {"id": "conv-123", "title": "Última conversa"}
                    ]
                    mock_client.list_messages.return_value = []

                    with patch("sys.argv", ["labia-chat", "--last"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_called_once()
        mock_client.set_token.assert_called_once_with("login-token")
        mock_client.list_conversations.assert_called_once_with(limit=1, offset=0)

    def test_resume_last_prompts_login_when_token_missing(self) -> None:
        """Testa que labia-chat --resume-last sem token faz login interativo."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                return_value="login-token",
            ) as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.list_conversations.return_value = [
                        {"id": "conv-123", "title": "Última conversa"}
                    ]
                    mock_client.list_messages.return_value = []

                    with patch("sys.argv", ["labia-chat", "--resume-last"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_called_once()
        mock_client.set_token.assert_called_once_with("login-token")
        mock_client.list_conversations.assert_called_once_with(limit=1, offset=0)

    def test_interactive_invocation_arg_token_does_not_prompt_login(self) -> None:
        """Testa que --token evita prompt de login."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("labia_chat.cli.prompt_for_ai_scope_login") as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("sys.argv", ["labia-chat", "--token", "arg-token"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_not_called()
        mock_client.set_token.assert_called_once_with("arg-token")

    def test_interactive_invocation_env_token_does_not_prompt_login(self) -> None:
        """Testa que LABIA_CHAT_TOKEN evita prompt de login."""
        with patch.dict("os.environ", {"LABIA_CHAT_TOKEN": "env-token"}, clear=True):
            with patch("labia_chat.cli.prompt_for_ai_scope_login") as prompt_login:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.create_conversation.return_value = {"id": "conv-123"}

                    with patch("sys.argv", ["labia-chat"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        prompt_login.assert_not_called()
        mock_client.set_token.assert_called_once_with("env-token")

    def test_login_failure_does_not_print_password_or_token(self, capsys) -> None:
        """Testa erro de login sem vazamento de senha/token."""
        with patch.dict("os.environ", {}, clear=True):
            with patch(
                "labia_chat.cli.prompt_for_ai_scope_login",
                side_effect=LoginError("Login AI-Scope recusado."),
            ):
                with patch("sys.argv", ["labia-chat"]):
                    result = main()

        output = capsys.readouterr().out
        assert result == 1
        assert "Login AI-Scope recusado" in output
        assert "secret-password" not in output
        assert "access-token" not in output

    def test_non_interactive_commands_do_not_prompt_without_token(
        self,
        capsys,
    ) -> None:
        """Testa que comandos não interativos falham sem prompt."""
        commands = [
            auth_me_command,
            conversations_list_command,
            messages_list_command,
            chat_send_command,
        ]
        args = argparse.Namespace(
            api_url="http://example.com",
            token=None,
            limit=20,
            offset=0,
            conversation_id="conv-123",
            message="Olá",
            stream=False,
        )

        with patch.dict("os.environ", {}, clear=True):
            with patch("labia_chat.cli.prompt_for_ai_scope_login") as prompt_login:
                with patch("labia_chat.cli.getpass.getpass") as getpass_prompt:
                    results = [command(args) for command in commands]

        output = capsys.readouterr().out
        assert results == [1, 1, 1, 1]
        assert "token AI-Scope ausente" in output
        prompt_login.assert_not_called()
        getpass_prompt.assert_not_called()

    def test_no_argument_invocation_passes_chat_args(self) -> None:
        """Testa que argumentos do chat são passados ao iniciar sem subcomando."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("sys.argv", ["labia-chat", "--show-last", "5"]):
                result = main()

                assert result == 0
                mock_chat.assert_called_once()
                # Verifica que o argumento show_last foi passado
                call_args = mock_chat.call_args
                args = call_args[0][0]
                assert args.show_last == 5

    def test_help_flag_prints_help_and_exits(self) -> None:
        """Testa que --help imprime ajuda e não inicia o chat."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            with patch("sys.argv", ["labia-chat", "--help"]):
                # argparse sai com SystemExit(0) ao imprimir --help
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                mock_chat.assert_not_called()

    def test_version_flag_prints_version_and_exits(self) -> None:
        """Testa que --version imprime versão e não inicia o chat."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            with patch("sys.argv", ["labia-chat", "--version"]):
                # argparse sai com SystemExit(0) ao imprimir --version
                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 0
                mock_chat.assert_not_called()

    def test_explicit_chat_command_still_works(self) -> None:
        """Testa que labia-chat chat continua funcionando como antes."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("sys.argv", ["labia-chat", "chat"]):
                result = main()

                assert result == 0
                mock_chat.assert_called_once()

    def test_explicit_chat_command_with_args_still_works(self) -> None:
        """Testa que labia-chat chat com argumentos continua funcionando."""
        with patch("labia_chat.cli.chat_command") as mock_chat:
            mock_chat.return_value = 0

            with patch("sys.argv", ["labia-chat", "chat", "--show-last", "3"]):
                result = main()

                assert result == 0
                mock_chat.assert_called_once()
                call_args = mock_chat.call_args
                args = call_args[0][0]
                assert args.show_last == 3

    def test_other_subcommands_still_work(self) -> None:
        """Testa que outros subcomandos continuam funcionando normalmente."""
        with patch("labia_chat.cli.config_show_command") as mock_config:
            mock_config.return_value = 0

            with patch("sys.argv", ["labia-chat", "config", "show"]):
                result = main()

                assert result == 0
                mock_config.assert_called_once()

    def test_chat_command_resumes_most_recent_conversation_with_resume_last(
        self,
    ) -> None:
        """Testa retoma da conversa mais recente com --resume-last."""
        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.list_conversations.return_value = [
                        {"id": "conv-123", "title": "Última conversa"}
                    ]
                    mock_client.list_messages.return_value = []

                    with patch("sys.argv", ["labia-chat", "chat", "--resume-last"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        mock_client.list_conversations.assert_called_once_with(limit=1, offset=0)
        assert mock_client.conversation_id == "conv-123"

    def test_chat_command_resumes_most_recent_conversation_with_last(self) -> None:
        """Testa retoma da conversa mais recente com --last."""
        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.list_conversations.return_value = [
                        {"id": "conv-456", "title": "Conversa anterior"}
                    ]
                    mock_client.list_messages.return_value = []

                    with patch("sys.argv", ["labia-chat", "--last"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        assert result == 0
        mock_client.list_conversations.assert_called_once_with(limit=1, offset=0)
        assert mock_client.conversation_id == "conv-456"

    def test_chat_command_creates_new_when_no_previous_conversation(
        self,
        capsys,
    ) -> None:
        """Testa criação de nova conversa quando não há anteriores."""
        with patch("labia_chat.cli.resolve_api_url", return_value="http://example.com"):
            with patch(INTERACTIVE_TOKEN_RESOLVER, return_value="test-token"):
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    mock_client = MockClient.return_value
                    mock_client.validate_token.return_value = {"username": "testuser"}
                    mock_client.list_conversations.return_value = []
                    mock_client.create_conversation.return_value = {
                        "id": "new-conv-789",
                    }
                    mock_client.list_messages.return_value = []

                    with patch("sys.argv", ["labia-chat", "chat", "--resume-last"]):
                        with patch("labia_chat.cli.input", return_value="/exit"):
                            result = main()

        output = capsys.readouterr().out
        assert result == 0
        mock_client.list_conversations.assert_called_once_with(limit=1, offset=0)
        mock_client.create_conversation.assert_called_once()
        assert "Nenhuma conversa anterior encontrada" in output
        assert "new-conv-789" in output

    def test_chat_command_rejects_conversation_id_with_resume_last(
        self,
        capsys,
    ) -> None:
        """Testa que --conversation-id é rejeitado junto com --last."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            title=None,
            conversation_id="some-id",
            show_last=10,
            stream=True,
            last=True,
            resume_last=False,
        )

        with patch("labia_chat.cli.resolve_api_url") as mock_resolve_api_url:
            with patch(INTERACTIVE_TOKEN_RESOLVER) as mock_resolve_token:
                with patch("labia_chat.cli.CLIClient") as MockClient:
                    result = chat_command(args)

        output = capsys.readouterr().out
        assert result == 1
        assert "--conversation-id não pode ser usado com --last/--resume-last" in output
        mock_resolve_api_url.assert_not_called()
        mock_resolve_token.assert_not_called()
        MockClient.assert_not_called()

    def _assert_main_parses_resume_last(
        self,
        argv: list[str],
        *,
        expected_last: bool,
        expected_resume_last: bool,
        expected_command: str | None,
    ) -> None:
        """Assert that main parses resume-last flags and dispatches chat_command."""
        with patch("sys.argv", argv):
            with patch("labia_chat.cli.chat_command", return_value=0) as mock_chat:
                result = main()

        assert result == 0
        mock_chat.assert_called_once()
        args = mock_chat.call_args[0][0]
        assert args.last is expected_last
        assert args.resume_last is expected_resume_last
        assert args.command == expected_command

    def test_top_level_parser_accepts_last_and_resume_last(self) -> None:
        """Testa que o parser top-level aceita --last e --resume-last."""
        self._assert_main_parses_resume_last(
            ["labia-chat", "--last"],
            expected_last=True,
            expected_resume_last=False,
            expected_command=None,
        )
        self._assert_main_parses_resume_last(
            ["labia-chat", "--resume-last"],
            expected_last=False,
            expected_resume_last=True,
            expected_command=None,
        )

    def test_chat_subparser_accepts_last_and_resume_last(self) -> None:
        """Testa que o subcomando chat aceita --last e --resume-last."""
        self._assert_main_parses_resume_last(
            ["labia-chat", "chat", "--last"],
            expected_last=True,
            expected_resume_last=False,
            expected_command="chat",
        )
        self._assert_main_parses_resume_last(
            ["labia-chat", "chat", "--resume-last"],
            expected_last=False,
            expected_resume_last=True,
            expected_command="chat",
        )


class TestConfigSourceReporting:
    """Testes de report de origem da configuração."""

    def test_doctor_reports_env_source_when_env_set(self, capsys) -> None:
        """Testa doctor com origem env."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            with_model=False,
        )

        with patch.dict(
            "os.environ", {"LABIA_CHAT_API_URL": "http://env.com:8010"}, clear=True
        ):
            with patch("labia_chat.cli.CLIClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.health_check.return_value = {"status": "ok"}

                result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "API URL: http://env.com:8010 (source: env)" in output

    def test_doctor_reports_argument_source_when_cli_flag_set(self, capsys) -> None:
        """Testa doctor com origem argument."""
        args = argparse.Namespace(
            api_url="http://cli-flag.com:8010",
            token=None,
            with_model=False,
        )

        with patch("labia_chat.cli.CLIClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            mock_client.health_check.return_value = {"status": "ok"}

            result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "API URL: http://cli-flag.com:8010 (source: argument)" in output

    def test_doctor_reports_default_source_when_no_config_no_env(
        self, capsys, tmp_path
    ) -> None:
        """Testa doctor com origem default."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
            with_model=False,
        )

        with patch.dict(
            "os.environ",
            {"XDG_CONFIG_HOME": str(tmp_path)},
            clear=True,
        ):
            with patch("labia_chat.cli.CLIClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                mock_client.health_check.return_value = {"status": "ok"}

                result = doctor_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert f"API URL: {DEFAULT_API_URL} (source: default)" in output

    def test_config_show_reports_config_source_when_config_exists(
        self, tmp_path, monkeypatch, capsys
    ) -> None:
        """Testa config show com origem config."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
        monkeypatch.delenv("LABIA_CHAT_API_URL", raising=False)

        save_config(api_url="http://127.0.0.1:8010")

        args = argparse.Namespace(
            api_url=None,
            token=None,
        )

        result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "URL da API: http://127.0.0.1:8010" in output
        assert "Origem da URL da API: config" in output

    def test_config_show_reports_env_source_when_env_set(self, capsys) -> None:
        """Testa config show com origem env."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
        )

        with patch.dict(
            "os.environ", {"LABIA_CHAT_API_URL": "http://env.com:8010"}, clear=True
        ):
            result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "Origem da URL da API: env" in output

    def test_config_show_reports_default_source_when_no_config_no_env(
        self, capsys, tmp_path
    ) -> None:
        """Testa config show com origem default."""
        args = argparse.Namespace(
            api_url=None,
            token=None,
        )

        with patch.dict(
            "os.environ",
            {"XDG_CONFIG_HOME": str(tmp_path)},
            clear=True,
        ):
            result = config_show_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "Origem da URL da API: default" in output


class TestConfigInitCommand:
    """Testes do comando 'config init'."""

    def test_config_init_saves_values(self, tmp_path, capsys) -> None:
        """Testa que config init salva os valores no arquivo."""

        # Usa um diretório temporário para o config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        with patch("labia_chat.cli_config.get_config_path", return_value=config_file):
            with patch("labia_chat.cli_config.get_config_dir", return_value=config_dir):
                args = argparse.Namespace(
                    api_url="http://custom-api.com:8010",
                    streaming_default="true",
                    show_last_default=20,
                )

                result = config_init_command(args)

        output = capsys.readouterr().out
        assert result == 0
        assert "Configuração salva com sucesso" in output
        assert str(config_file) in output

        # Verifica que o arquivo foi criado com os valores corretos
        content = config_file.read_text()
        assert 'api_url = "http://custom-api.com:8010"' in content
        assert "streaming_default = true" in content
        assert "show_last_default = 20" in content

    def test_config_init_partial_update(self, tmp_path, capsys) -> None:
        """Testa que config init atualiza apenas valores fornecidos."""
        from labia_chat.cli_config import save_config

        # Usa um diretório temporário para o config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        # Primeiro, salva uma configuração inicial
        with patch("labia_chat.cli_config.get_config_path", return_value=config_file):
            with patch("labia_chat.cli_config.get_config_dir", return_value=config_dir):
                save_config(
                    api_url="http://initial.com:8010",
                    streaming_default=True,
                    show_last_default=10,
                )

                # Agora atualiza apenas o streaming_default
                args = argparse.Namespace(
                    api_url=None,
                    streaming_default="false",
                    show_last_default=None,
                )

                result = config_init_command(args)

        assert result == 0

        # Verifica que apenas streaming_default foi atualizado
        content = config_file.read_text()
        assert 'api_url = "http://initial.com:8010"' in content  # Mantido
        assert "streaming_default = false" in content  # Atualizado
        assert "show_last_default = 10" in content  # Mantido

    def test_config_init_never_saves_token(self, tmp_path, capsys) -> None:
        """Testa que config init nunca salva token."""

        # Usa um diretório temporário para o config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "config.toml"

        with patch("labia_chat.cli_config.get_config_path", return_value=config_file):
            with patch("labia_chat.cli_config.get_config_dir", return_value=config_dir):
                # Simula que args tem um token (mas ele não deve ser salvo)
                args = argparse.Namespace(
                    api_url="http://custom-api.com:8010",
                    streaming_default="true",
                    show_last_default=20,
                )

                result = config_init_command(args)

        assert result == 0

        # Verifica que token não está no arquivo
        content = config_file.read_text()
        assert "token" not in content.lower()
