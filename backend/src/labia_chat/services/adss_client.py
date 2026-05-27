"""Cliente HTTP para o AI-Scope ADSS."""

import asyncio
from http import HTTPStatus

import httpx

from labia_chat.core.config import settings
from labia_chat.core.errors import (
    AuthenticationError,
    ExternalServiceError,
)
from labia_chat.schemas.user import ADSSUser


class AdssClient:
    """Cliente para comunicação com o AI-Scope ADSS."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ):
        """
        Inicializa o cliente ADSS.

        Args:
            base_url: URL base do ADSS. Se não fornecida, usa settings.adss_base_url.
            timeout:
                Timeout em segundos para requisições. Se não fornecido, usa
                settings.adss_timeout_seconds.
        """
        self.base_url = base_url or settings.adss_base_url.rstrip("/")
        self.timeout = timeout or settings.adss_timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "AdssClient":
        """Entrar no contexto assíncrono."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sair do contexto assíncrono."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_user_info(self, token: str) -> ADSSUser:
        """
        Recupera informações do usuário do ADSS.

        Args:
            token: Token de autenticação Bearer.

        Returns:
            ADSSUser: Objeto com informações do usuário.

        Raises:
            AuthenticationError: Se o token for inválido (401/403).
            ExternalServiceError: Se houver erro de rede ou timeout.
        """
        if not self._client:
            raise RuntimeError("AdssClient must be used as async context manager")

        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await self._client.get("/users/me", headers=headers)
        except asyncio.TimeoutError as exc:
            raise ExternalServiceError(
                f"Request to ADSS timed out after {self.timeout}s"
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalServiceError(
                f"Failed to connect to ADSS: {exc}"
            ) from exc

        if response.status_code == HTTPStatus.UNAUTHORIZED:
            raise AuthenticationError("Invalid or expired token")
        if response.status_code == HTTPStatus.FORBIDDEN:
            raise AuthenticationError("Token not authorized for this resource")

        response.raise_for_status()

        return ADSSUser(**response.json())
