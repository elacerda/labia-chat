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
        Valida um token de autenticação e verifica as roles do usuário.

        Args:
            token: Token de autenticação Bearer.

        Returns:
            AuthenticatedUser: Objeto normalizado com informações do usuário.

        Raises:
            AuthenticationError: Se o token for inválido ou expirado.
            AuthorizationError: Se o usuário estiver inativo ou sem role exigida.
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

        # Valida se usuário está ativo
        if not adss_user.is_active:
            raise AuthorizationError("User is not active")

        # Valida se usuário tem a role exigida
        required_role = settings.adss_required_role
        user_roles = [role.name for role in adss_user.roles]

        if required_role not in user_roles:
            raise AuthorizationError(
                f"User does not have required role '{required_role}'. "
                f"Available roles: {user_roles}"
            )

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
