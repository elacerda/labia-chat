"""Testes de integração HTTP para o endpoint /auth/me."""

from fastapi.testclient import TestClient

from labia_chat.api.deps import get_auth_service
from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.main import app
from labia_chat.schemas.user import AuthenticatedUser

client = TestClient(app)


class FakeAuthService:
    """Fake de AuthService para testes (não chama ADSS real)."""

    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Retorna usuário ou levanta erro."""
        if self.error:
            raise self.error
        return self.user



def test_get_auth_me_without_authorization_header() -> None:
    """Testa GET /auth/me sem Authorization header -> 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_auth_me_with_malformed_authorization() -> None:
    """Testa GET /auth/me com Authorization malformado -> 401."""
    response = client.get("/auth/me", headers={"Authorization": "InvalidFormat"})
    assert response.status_code == 401
    assert "Invalid authorization format" in response.json()["detail"]


def test_get_auth_me_with_valid_token_and_user() -> None:
    """Testa GET /auth/me com Bearer token válido -> 200."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["public", "chat_vllm"],
    )

    def fake_get_auth_service_override():
        return FakeAuthService(user=mock_user)

    app.dependency_overrides[get_auth_service] = (
        fake_get_auth_service_override
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "user123"
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True
        assert data["roles"] == ["public", "chat_vllm"]
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_authentication_error() -> None:
    """Testa GET /auth/me com AuthenticationError -> 401."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        error=AuthenticationError("Invalid or expired token")
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired token"
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_authorization_error() -> None:
    """Testa GET /auth/me com AuthorizationError -> 403."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        error=AuthorizationError("User does not have required role")
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 403
        assert "does not have required role" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_external_service_error() -> None:
    """Testa GET /auth/me com ExternalServiceError -> 503."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        error=ExternalServiceError("Service unavailable")
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Service unavailable"
    finally:
        app.dependency_overrides.clear()
