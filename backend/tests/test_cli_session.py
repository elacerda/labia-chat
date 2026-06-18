"""Testes do módulo de session CLI (cli_session.py)."""

import json
import os
from pathlib import Path
from unittest.mock import patch

from labia_chat.cli_session import (
    clear_session,
    get_cached_session,
    get_session_dir,
    get_session_path,
    load_session,
    save_session,
)


class TestGetSessionDir:
    """Testes da função get_session_dir."""

    def test_uses_xdg_state_home_when_set(self, tmp_path) -> None:
        """Testa que XDG_STATE_HOME é usado quando definido."""
        with patch.dict(os.environ, {"XDG_STATE_HOME": str(tmp_path)}):
            result = get_session_dir()
            assert result == tmp_path / "labia-chat"

    def test_uses_default_when_xdg_not_set(self) -> None:
        """Testa que o padrão é usado quando XDG_STATE_HOME não está definido."""
        with patch.dict(os.environ, {"XDG_STATE_HOME": ""}, clear=True):
            with patch.object(Path, "home", return_value=Path("/home/test")):
                result = get_session_dir()
                assert result == Path("/home/test") / ".local" / "state" / "labia-chat"


class TestGetSessionPath:
    """Testes da função get_session_path."""

    def test_returns_session_file_in_session_dir(self) -> None:
        """Testa que o caminho do arquivo é retornado corretamente."""
        with patch("labia_chat.cli_session.get_session_dir") as mock_dir:
            mock_dir.return_value = Path("/tmp/test-session")
            result = get_session_path()
            assert result == Path("/tmp/test-session") / "session.json"


class TestLoadSession:
    """Testes da função load_session."""

    def test_returns_none_when_file_not_exists(self, tmp_path) -> None:
        """Testa que None é retornado quando o arquivo não existe."""
        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = tmp_path / "nonexistent.json"
            result = load_session()
            assert result is None

    def test_returns_dict_when_file_exists(self, tmp_path) -> None:
        """Testa que dict é retornado quando o arquivo existe."""
        session_file = tmp_path / "session.json"
        session_data = {"access_token": "test-token-123", "username": "testuser"}
        session_file.write_text(json.dumps(session_data))

        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = session_file
            result = load_session()
            assert result == session_data

    def test_returns_none_when_file_invalid_json(self, tmp_path) -> None:
        """Testa que None é retornado quando o JSON é inválido."""
        session_file = tmp_path / "session.json"
        session_file.write_text("invalid json {{")

        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = session_file
            result = load_session()
            assert result is None


class TestSaveSession:
    """Testes da função save_session."""

    def test_writes_session_file(self, tmp_path) -> None:
        """Testa que o arquivo de sessão é escrito."""
        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = tmp_path / "session.json"
            save_session("test-token", {"username": "testuser"})

            assert (tmp_path / "session.json").exists()
            content = (tmp_path / "session.json").read_text()
            data = json.loads(content)
            assert data["access_token"] == "test-token"
            assert data["username"] == "testuser"

    def test_sets_file_permissions_to_0o600(self, tmp_path) -> None:
        """Testa que as permissões do arquivo são 0o600."""
        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = tmp_path / "session.json"
            save_session("test-token", {"username": "testuser"})

            mode = os.stat(tmp_path / "session.json").st_mode
            assert mode & 0o777 == 0o600

    def test_writes_metadata_fields(self, tmp_path) -> None:
        """Testa que campos de metadata são escritos."""
        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = tmp_path / "session.json"
            save_session(
                "test-token",
                {
                    "username": "testuser",
                    "api_url": "http://example.com",
                },
            )

            content = (tmp_path / "session.json").read_text()
            data = json.loads(content)
            assert data["access_token"] == "test-token"
            assert data["username"] == "testuser"
            assert data["api_url"] == "http://example.com"

    def test_skips_none_values(self, tmp_path) -> None:
        """Testa que valores None são ignorados."""
        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = tmp_path / "session.json"
            save_session(
                "test-token",
                {
                    "username": "testuser",
                    "api_url": None,
                },
            )

            content = (tmp_path / "session.json").read_text()
            data = json.loads(content)
            assert "api_url" not in data


class TestClearSession:
    """Testes da função clear_session."""

    def test_removes_session_file_when_exists(self, tmp_path) -> None:
        """Testa que o arquivo é removido quando existe."""
        session_file = tmp_path / "session.json"
        session_file.write_text('{"access_token": "test"}')

        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = session_file
            clear_session()

            assert not session_file.exists()

    def test_does_not_error_when_file_missing(self, tmp_path) -> None:
        """Testa que clear_session não gera erro quando o arquivo não existe."""
        session_file = tmp_path / "session.json"
        assert not session_file.exists()

        with patch("labia_chat.cli_session.get_session_path") as mock_path:
            mock_path.return_value = session_file
            clear_session()  # Should not raise


class TestGetCachedSession:
    """Testes da função get_cached_session."""

    def test_returns_none_when_no_session(self, tmp_path) -> None:
        """Testa que None é retornado quando não há sessão."""
        with patch("labia_chat.cli_session.load_session") as mock_load:
            mock_load.return_value = None
            result = get_cached_session()
            assert result is None

    def test_returns_none_when_empty_token(self, tmp_path) -> None:
        """Testa que None é retornado quando o token está vazio."""
        with patch("labia_chat.cli_session.load_session") as mock_load:
            with patch("labia_chat.cli_session.clear_session") as mock_clear:
                mock_load.return_value = {"access_token": ""}
                result = get_cached_session()
                assert result is None
                mock_clear.assert_called_once()

    def test_returns_stripped_token(self, tmp_path) -> None:
        """Testa que o token é stripado antes de ser retornado."""
        with patch("labia_chat.cli_session.load_session") as mock_load:
            mock_load.return_value = {"access_token": "  test-token  "}
            result = get_cached_session()
            assert result == "test-token"

    def test_returns_valid_token(self, tmp_path) -> None:
        """Testa que o token válido é retornado."""
        with patch("labia_chat.cli_session.load_session") as mock_load:
            mock_load.return_value = {"access_token": "valid-token-123"}
            result = get_cached_session()
            assert result == "valid-token-123"
