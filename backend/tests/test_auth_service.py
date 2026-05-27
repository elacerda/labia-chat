"""Testes unitários para o AuthService e AdssClient."""


import pytest

from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.schemas.user import ADSSRole, ADSSUser
from labia_chat.services.adss_client import AdssClient
from labia_chat.services.auth_service import AuthService


# Fixture para criar um AdssClient com configuração de teste
@pytest.fixture
def adss_client():
    """Cria um AdssClient com URL de teste."""
    return AdssClient(
        base_url="https://ai-scope.cbpf.br/adss/v1",
        timeout=10.0,
    )


class FakeAdssClient:
    """Fake simples para AdssClient com suporte a async context manager."""

    def __init__(self, user_info=None, error=None):
        self.user_info = user_info
        self.error = error
        self.call_count = 0

    async def __aenter__(self):
        """Entrar no contexto assíncrono."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Sair do contexto assíncrono."""
        pass

    async def get_user_info(self, token: str) -> ADSSUser:
        """Retorna informações do usuário ou levanta erro."""
        self.call_count += 1
        if self.error:
            raise self.error
        return self.user_info


class TestAuthService:
    """Testes para AuthService (camada interna ADSS)."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Testa validação de token com usuário ativo e role exigida."""
        mock_adss_user = ADSSUser(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=[
                ADSSRole(id=1, name="public", description="Public role"),
                ADSSRole(id=2, name="chat_vllm", description="Chat vLLM role"),
            ],
        )

        fake_client = FakeAdssClient(user_info=mock_adss_user)
        auth_service = AuthService(adss_client=fake_client)

        result = await auth_service.validate_token("valid-token")

        assert result.id == "user123"
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.full_name == "Test User"
        assert result.is_active is True
        assert result.is_staff is False
        assert result.is_superuser is False
        assert "chat_vllm" in result.roles
        assert "public" in result.roles

    @pytest.mark.asyncio
    async def test_validate_token_user_inactive(self):
        """Testa validação com usuário inativo."""
        mock_adss_user = ADSSUser(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=False,
            is_staff=False,
            is_superuser=False,
            roles=[
                ADSSRole(id=1, name="public", description="Public role"),
            ],
        )

        fake_client = FakeAdssClient(user_info=mock_adss_user)
        auth_service = AuthService(adss_client=fake_client)

        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.validate_token("valid-token")

        assert "User is not active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_missing_role(self):
        """Testa validação com usuário sem role exigida."""
        mock_adss_user = ADSSUser(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=[
                ADSSRole(id=1, name="public", description="Public role"),
                ADSSRole(id=2, name="other_role", description="Other role"),
            ],
        )

        fake_client = FakeAdssClient(user_info=mock_adss_user)
        auth_service = AuthService(adss_client=fake_client)

        with pytest.raises(AuthorizationError) as exc_info:
            await auth_service.validate_token("valid-token")

        assert "does not have required role" in str(exc_info.value)
        assert "chat_vllm" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_adss_role_without_description(self):
        """Testa que ADSSRole pode ser criada sem description."""
        role = ADSSRole(id=1, name="public")

        assert role.id == 1
        assert role.name == "public"
        assert role.description is None

    @pytest.mark.asyncio
    async def test_validate_token_adss_unauthorized(self):
        """Testa validação com erro 401 do ADSS."""
        fake_client = FakeAdssClient(
            error=AuthenticationError("Invalid or expired token")
        )
        auth_service = AuthService(adss_client=fake_client)

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.validate_token("invalid-token")

        assert "Invalid or expired token" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_token_adss_external_error(self):
        """Testa validação com erro externo do ADSS."""
        fake_client = FakeAdssClient(
            error=ExternalServiceError("Service unavailable")
        )
        auth_service = AuthService(adss_client=fake_client)

        with pytest.raises(ExternalServiceError) as exc_info:
            await auth_service.validate_token("invalid-token")

        assert "Service unavailable" in str(exc_info.value)
