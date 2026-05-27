"""Dependências FastAPI para autenticação e autorização."""

from fastapi import Depends, Header, HTTPException

from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.schemas.user import AuthenticatedUser
from labia_chat.services.auth_service import AuthService
from labia_chat.services.chat_user_sync import ChatUserSyncService


def get_auth_service() -> AuthService:
    """
    Retorna instância de AuthService.

    Pode ser sobrescrita via dependency_overrides nos testes.
    """
    return AuthService()


def get_chat_user_sync_service() -> ChatUserSyncService:
    """
    Retorna instância de ChatUserSyncService.

    Pode ser sobrescrita via dependency_overrides nos testes.
    """
    return ChatUserSyncService()


def extract_bearer_token(
    authorization: str | None,
) -> str:
    """
    Extrai o token Bearer do header Authorization.

    Args:
        authorization: Valor do header Authorization.

    Returns:
        O token Bearer.

    Raises:
        HTTPException 401: Se authorization for None ou malformado.
    """
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    # Formato esperado: "Bearer <token>"
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Use 'Bearer <token>'",
        )

    token = parts[1].strip()
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization format. Token is empty",
        )

    return token


async def get_current_user(
    authorization: str | None = Header(None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
    chat_user_sync_service: ChatUserSyncService = Depends(get_chat_user_sync_service),
) -> AuthenticatedUser:
    """
    Dependência para obter usuário autenticado.

    Args:
        authorization: Header Authorization (injetado pelo FastAPI).
        auth_service: Instância de AuthService (injetada por Depends).
        chat_user_sync_service: Instância de ChatUserSyncService (injetada por Depends).

    Returns:
        AuthenticatedUser se o token for válido.

    Raises:
        HTTPException 401: Se o token for inválido ou ausente.
        HTTPException 403: Se o usuário não tiver permissão.
        HTTPException 503: Se o serviço externo estiver indisponível ou
        falha ao sincronizar.
    """
    token = extract_bearer_token(authorization)

    try:
        user = await auth_service.validate_token(token)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail=exc.message,
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(
            status_code=403,
            detail=exc.message,
        ) from exc
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=exc.message,
        ) from exc

    # Sincroniza usuário no banco após validação bem-sucedida
    try:
        await chat_user_sync_service.sync(user)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=exc.message,
        ) from exc

    return user
