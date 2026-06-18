"""Helpers de autenticação interativa do CLI."""

import getpass
from collections.abc import Callable

import httpx

AI_SCOPE_LOGIN_URL = "https://ai-scope.cbpf.br/adss/v1/auth/login"


class LoginError(Exception):
    """Erro de login AI-Scope no CLI."""


def login_ai_scope(
    username: str,
    password: str,
    *,
    login_url: str = AI_SCOPE_LOGIN_URL,
    timeout: float = 30.0,
) -> str:
    """
    Autentica no AI-Scope ADSS e retorna o access_token.

    O token retornado deve permanecer apenas em memória no processo CLI.
    """
    try:
        response = httpx.post(
            login_url,
            data={"username": username, "password": password},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            raise LoginError(
                "Login AI-Scope recusado. Verifique usuário e senha."
            ) from exc
        raise LoginError("Não foi possível autenticar no AI-Scope.") from exc
    except httpx.TimeoutException as exc:
        raise LoginError("Timeout ao autenticar no AI-Scope. Tente novamente.") from exc
    except httpx.NetworkError as exc:
        raise LoginError(
            "Falha de conexão com o AI-Scope. Verifique sua rede."
        ) from exc
    except ValueError as exc:
        raise LoginError("Resposta inesperada do AI-Scope.") from exc

    access_token = data.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise LoginError("Resposta do AI-Scope não incluiu access_token.")

    return access_token.strip()


def prompt_for_ai_scope_login(
    *,
    input_func: Callable[[str], str] = input,
    password_func: Callable[[str], str] = getpass.getpass,
    login_func: Callable[[str, str], str] = login_ai_scope,
) -> str:
    """Solicita credenciais AI-Scope e retorna token de acesso em memória."""
    print("Login AI-Scope necessário para iniciar o chat.")
    username = input_func("AI-Scope username: ").strip()
    if not username:
        raise LoginError("Usuário AI-Scope não informado.")

    password = password_func("AI-Scope password: ")
    if not password:
        raise LoginError("Senha AI-Scope não informada.")

    return login_func(username, password)


def store_session_after_login(
    access_token: str,
    username: str,
    api_url: str,
) -> None:
    """
    Saves the session after successful login.

    Args:
        access_token: The AI-Scope access token.
        username: The authenticated username.
        api_url: The API URL used for authentication.
    """
    from labia_chat.cli_session import save_session

    save_session(
        access_token,
        {
            "username": username,
            "api_url": api_url,
        },
    )
