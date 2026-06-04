"""Configuração local do CLI labia-chat usando TOML."""

import os
import sys
from pathlib import Path

DEFAULT_API_URL = "http://orion.cbpf.br:8010"

# TOML leitura (Python 3.11+)
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib
    except ImportError:
        # Fallback para Python < 3.11 (não deve ocorrer no ambiente atual)
        tomllib = None  # type: ignore

# TOML escrita simples para valores escalares
def _write_simple_toml(data: dict) -> str:
    """Escreve TOML simples para um dicionário com valores escalares."""
    lines = []
    for key, value in data.items():
        if isinstance(value, bool):
            lines.append(f'{key} = {"true" if value else "false"}')
        elif isinstance(value, int):
            lines.append(f"{key} = {value}")
        elif isinstance(value, str):
            # Escape aspas duplas e barras invertidas
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"')
        elif value is None:
            lines.append(f'{key} = ""')
        else:
            # Fallback para string
            lines.append(f'{key} = "{value}"')
    return "\n".join(lines) + "\n"


def get_config_dir() -> Path:
    """
    Retorna o diretório de configuração do CLI.

    Usa XDG_CONFIG_HOME se definido, senão ~/.config.
    """
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / "labia-chat"
    try:
        home = Path.home()
    except RuntimeError:
        home = Path.cwd()
    return home / ".config" / "labia-chat"


def get_config_path() -> Path:
    """Retorna o caminho completo para o arquivo de configuração."""
    return get_config_dir() / "config.toml"


def load_config() -> dict:
    """
    Carrega a configuração local do arquivo TOML.

    Returns:
        Dicionário com os valores da configuração. Retorna dict vazio se não existir.
    """
    config_path = get_config_path()
    if not config_path.exists():
        return {}

    if tomllib is None:
        return {}

    try:
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def save_config(
    api_url: str | None = None,
    streaming_default: bool | None = None,
    show_last_default: int | None = None,
) -> None:
    """
    Salva a configuração local no arquivo TOML.

    Args:
        api_url: URL do backend (opcional).
        streaming_default: Habilitar streaming por padrão (opcional).
        show_last_default: Número de mensagens a exibir por padrão (opcional).
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()

    if api_url is not None:
        config["api_url"] = api_url
    if streaming_default is not None:
        config["streaming_default"] = streaming_default
    if show_last_default is not None:
        config["show_last_default"] = show_last_default

    config_path = get_config_path()
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(_write_simple_toml(config))


def delete_config() -> None:
    """Remove o arquivo de configuração se existir."""
    config_path = get_config_path()
    if config_path.exists():
        config_path.unlink()


def resolve_api_url_with_source(args_api_url: str | None) -> tuple[str, str]:
    """
    Resolve a URL da API na ordem: flag CLI > env > config > default.

    Args:
        args_api_url: Valor passado via --api-url.

    Returns:
        Tupla com URL resolvida e origem: argument, env, config ou default.
    """
    # 1. CLI args tem precedência
    if args_api_url:
        return args_api_url, "argument"

    # 2. Variável de ambiente
    env_url = os.environ.get("LABIA_CHAT_API_URL")
    if env_url:
        return env_url, "env"

    # 3. Arquivo de configuração local
    config = load_config()
    if "api_url" in config:
        return config["api_url"], "config"

    # 4. Default
    return DEFAULT_API_URL, "default"


def resolve_streaming_default_with_source(args_stream: bool | None) -> tuple[bool, str]:
    """
    Resolve se streaming deve ser usado por padrão.

    Args:
        args_stream: Valor passado via --stream/--no-stream (None se não especificado).

    Returns:
        Tupla com valor resolvido e origem: argument, config ou default.
    """
    # Se o usuário especificou explicitamente via CLI
    if args_stream is not None:
        return args_stream, "argument"

    # Configuração local
    config = load_config()
    if "streaming_default" in config:
        return config["streaming_default"], "config"

    # Default
    return True, "default"


def resolve_show_last_default_with_source(
    args_show_last: int | None,
) -> tuple[int, str]:
    """
    Resolve o número de mensagens a exibir no histórico.

    Args:
        args_show_last: Valor passado via --show-last.

    Returns:
        Tupla com valor resolvido e origem: argument, config ou default.
    """
    # CLI args tem precedência
    if args_show_last is not None:
        return args_show_last, "argument"

    # Configuração local
    config = load_config()
    if "show_last_default" in config:
        return config["show_last_default"], "config"

    # Default
    return 10, "default"


def resolve_token_optional_with_source(
    args_token: str | None,
) -> tuple[str | None, str]:
    """
    Resolve o token sem prompt interativo e com origem detectável.

    Args:
        args_token: Valor passado via --token.

    Returns:
        Tupla com token opcional e origem: argument, env, config ou missing.
        NUNCA retorna o token do config (tokens não são salvos no config).
    """
    # CLI args tem precedência
    if args_token:
        return args_token, "argument"

    # Variável de ambiente
    env_token = os.environ.get("LABIA_CHAT_TOKEN")
    if env_token:
        return env_token, "env"

    # Configuração local - NUNCA armazena tokens por segurança
    # Retorna missing para indicar que não há token configurado
    return None, "missing"
