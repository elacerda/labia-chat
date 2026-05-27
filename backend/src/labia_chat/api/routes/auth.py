"""Endpoint de autenticação /auth/me."""

from fastapi import APIRouter, Depends

from labia_chat.api.deps import get_current_user
from labia_chat.schemas.user import AuthenticatedUser

router = APIRouter()


@router.get("/auth/me")
async def get_auth_me(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """
    Valida token AI-Scope e retorna usuário normalizado.

    Request:
        GET /auth/me
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - AuthenticatedUser normalizado
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        503 Service Unavailable - Serviço externo indisponível
    """
    return user
