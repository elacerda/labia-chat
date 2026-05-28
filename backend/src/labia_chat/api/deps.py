"""Dependências FastAPI para autenticação e autorização."""

from contextlib import asynccontextmanager

from fastapi import Depends, Header, HTTPException

from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.models.user import ChatUser
from labia_chat.schemas.user import AuthenticatedUser
from labia_chat.services.auth_service import AuthService
from labia_chat.services.chat_generation import ChatGenerationService
from labia_chat.services.chat_persistence import ChatPersistenceService
from labia_chat.services.chat_user_sync import ChatUserSyncService
from labia_chat.services.vllm_client import VLLMClient


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


def get_chat_persistence_service() -> ChatPersistenceService:
    """
    Retorna instância de ChatPersistenceService.

    Pode ser sobrescrita via dependency_overrides nos testes.
    """
    return ChatPersistenceService()


def get_vllm_client() -> VLLMClient:
    """
    Retorna instância de VLLMClient.

    Pode ser sobrescrita via dependency_overrides nos testes.
    """
    return VLLMClient()


@asynccontextmanager
async def get_vllm_service():
    """
    Retorna instância de ChatGenerationService com VLLMClient gerenciado.

    Gerencia o ciclo de vida do VLLMClient como async context manager
    para garantir que a conexão HTTP seja aberta e fechada corretamente.

    Pode ser sobrescrita via dependency_overrides nos testes.

    Yields:
        ChatGenerationService: Serviço de geração de chat.
    """
    async with VLLMClient() as vllm_client:
        yield ChatGenerationService(vllm_client=vllm_client)


def get_chat_generation_service() -> ChatGenerationService:
    """
    Retorna instância de ChatGenerationService.

    Cria um ChatGenerationService usando VLLMClient configurado por settings.
    Pode ser sobrescrita via dependency_overrides nos testes.

    Returns:
        ChatGenerationService: Serviço de geração de chat.
    """
    return ChatGenerationService(vllm_client=VLLMClient())


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


async def _validate_and_sync_user(
    authorization: str | None,
    auth_service: AuthService,
    chat_user_sync_service: ChatUserSyncService,
) -> tuple[AuthenticatedUser, ChatUser]:
    """
    Valida token e sincroniza usuário local.

    Esta função encapsula a lógica de:
    - Extrair Bearer token
    - Validar token via AuthService
    - Sincronizar usuário via ChatUserSyncService

    Args:
        authorization: Header Authorization.
        auth_service: Instância de AuthService.
        chat_user_sync_service: Instância de ChatUserSyncService.

    Returns:
        Tuple[AuthenticatedUser, ChatUser]: Usuário autenticado e usuário local.

    Raises:
        HTTPException 401: Se o token for inválido ou ausente.
        HTTPException 403: Se o usuário não tiver permissão.
        HTTPException 503: Se o serviço externo estiver indisponível.
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
        chat_user = await chat_user_sync_service.sync(user)
    except ExternalServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=exc.message,
        ) from exc

    return user, chat_user


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
        HTTPException 503: Se o serviço externo estiver indisponível.
    """
    user, _ = await _validate_and_sync_user(
        authorization, auth_service, chat_user_sync_service
    )
    return user


async def get_current_chat_user(
    authorization: str | None = Header(None, alias="Authorization"),
    auth_service: AuthService = Depends(get_auth_service),
    chat_user_sync_service: ChatUserSyncService = Depends(get_chat_user_sync_service),
) -> ChatUser:
    """
    Dependência para obter usuário local (ChatUser) autenticado.

    Esta função é usada por endpoints de chat que precisam do ID interno
    do usuário (ChatUser.id) para garantir ownership de conversas e mensagens.

    Args:
        authorization: Header Authorization (injetado pelo FastAPI).
        auth_service: Instância de AuthService (injetada por Depends).
        chat_user_sync_service: Instância de ChatUserSyncService (injetada por Depends).

    Returns:
        ChatUser: Usuário local sincronizado com o ADSS.

    Raises:
        HTTPException 401: Se o token for inválido ou ausente.
        HTTPException 403: Se o usuário não tiver permissão.
        HTTPException 503: Se o serviço externo estiver indisponível.
    """
    _, chat_user = await _validate_and_sync_user(
        authorization, auth_service, chat_user_sync_service
    )
    return chat_user
