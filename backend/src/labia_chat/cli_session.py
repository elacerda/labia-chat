"""Session management for CLI authentication state."""

import os
import stat
from pathlib import Path
from typing import Any

# Prefer tomllib for Python 3.11+, fallback for older versions
try:
    import tomllib
except ImportError:
    try:
        import tomllib
    except ImportError:
        tomllib = None  # type: ignore

# TOML writing helper (simple, scalar-only)
def _write_simple_toml(data: dict) -> str:
    """Write simple TOML for scalar values."""
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f'{key} = {"true" if value else "false"}')
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif value is None:
            lines.append(f'{key} = ""')
        else:
            lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def get_session_dir() -> Path:
    """
    Returns the directory for session storage.

    Uses XDG_STATE_HOME if defined, otherwise ~/.local/state.

    Returns:
        Path to the session directory.
    """
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / "labia-chat"
    try:
        home = Path.home()
    except RuntimeError:
        home = Path.cwd()
    return home / ".local" / "state" / "labia-chat"


def get_session_path() -> Path:
    """
    Returns the full path to the session file.

    Returns:
        Path to session.json in the session directory.
    """
    return get_session_dir() / "session.json"


def load_session() -> dict | None:
    """
    Loads the session from the session file.

    Returns:
        Session dict if file exists and parseable, None otherwise.
    """
    session_path = get_session_path()
    if not session_path.exists():
        return None

    try:
        with open(session_path, "r", encoding="utf-8") as f:
            import json
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def save_session(access_token: str, metadata: dict[str, Any]) -> None:
    """
    Saves the session to the session file with restrictive permissions.

    Args:
        access_token: The AI-Scope access token.
        metadata: Additional session metadata (username, api_url, etc.).
    """
    session_dir = get_session_dir()
    session_dir.mkdir(parents=True, exist_ok=True)

    session_path = get_session_path()
    data = {
        "access_token": access_token,
        **{k: v for k, v in metadata.items() if v is not None},
    }

    # Write with restrictive permissions
    with open(session_path, "w", encoding="utf-8") as f:
        import json
        json.dump(data, f, indent=2)

    # Set file permissions to 0o600 (user read/write only)
    os.chmod(session_path, stat.S_IRUSR | stat.S_IWUSR)


def clear_session() -> None:
    """
    Removes the session file if it exists.
    """
    session_path = get_session_path()
    if session_path.exists():
        session_path.unlink()


def get_cached_session() -> str | None:
    """
    Returns the cached access token if available and valid.

    Returns:
        The access token string if valid, None otherwise.
    """
    session = load_session()
    if session is None:
        return None

    # Check required field
    access_token = session.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        clear_session()
        return None

    return access_token.strip()
