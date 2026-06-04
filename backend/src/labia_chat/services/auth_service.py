"""Serviço de autenticação e autorização."""

from labia_chat.core.config import settings
from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.schemas.user import ADSSUser, AuthenticatedUser
from labia_chat.services.adss_client import AdssClient


class AuthService:
    """Serviço para validação de autenticação e autorização via ADSS."""

    def __init__(self, adss_client: AdssClient | None = None):
        """
        Inicializa o AuthService.

        Args:
            adss_client: Instância de AdssClient. Se não fornecida, cria uma nova.
        """
        self._adss_client = adss_client or AdssClient()

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """
        Valida um token de autenticação.

        Args:
            token: Token de autenticação Bearer.

        Returns:
            AuthenticatedUser: Objeto normalizado com informações do usuário.

        Raises:
            AuthenticationError: Se o token for inválido ou expirado.
            ExternalServiceError: Se o serviço externo (ADSS) estiver indisponível.
        """
        async with self._adss_client as client:
            try:
                adss_user: ADSSUser = await client.get_user_info(token)
            except AuthenticationError:
                raise
            except ExternalServiceError:
                raise
            except Exception as exc:
                raise AuthenticationError(
                    f"Failed to validate authentication token: {exc}"
                ) from exc

        user_roles = [role.name for role in adss_user.roles]

        # Normaliza para AuthenticatedUser
        return AuthenticatedUser(
            id=adss_user.id,
            username=adss_user.username,
            email=adss_user.email,
            full_name=adss_user.full_name,
            is_active=adss_user.is_active,
            is_staff=adss_user.is_staff,
            is_superuser=adss_user.is_superuser,
            roles=user_roles,
        )

    def authorize_chat_access(self, user: AuthenticatedUser) -> None:
        """
        Verifica se um usuário autenticado pode acessar endpoints de chat.

        Args:
            user: Usuário autenticado e normalizado.

        Raises:
            AuthorizationError: Se o usuário estiver inativo ou sem role exigida.
        """
        if not user.is_active:
            raise AuthorizationError("Usuário AI-Scope inativo.")

        required_role = settings.adss_required_role
        if required_role not in user.roles:
            raise AuthorizationError(
                "Usuário sem permissão para usar o chat. "
                "Role necessária: chat_vllm."
            )
