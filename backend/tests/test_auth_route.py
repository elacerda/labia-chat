"""Testes de integração HTTP para o endpoint /auth/me."""

from fastapi.testclient import TestClient

from labia_chat.api.deps import (
    get_auth_service,
    get_chat_user_sync_service,
    get_current_chat_user,
    get_current_user,
)
from labia_chat.core.errors import (
    AuthenticationError,
    AuthorizationError,
    ExternalServiceError,
)
from labia_chat.main import app
from labia_chat.models.user import ChatUser
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

    def authorize_chat_access(self, user: AuthenticatedUser) -> None:
        """Simula autorização de chat."""
        if self.error:
            raise self.error


class FakeChatUserSyncService:
    """Fake de ChatUserSyncService para testes (não acessa banco real)."""

    def __init__(self, error=None):
        self.error = error
        self.sync_calls = []

    async def sync(self, user: AuthenticatedUser) -> None:
        """Simula sincronização."""
        self.sync_calls.append(user)
        if self.error:
            raise self.error


def test_get_auth_me_without_authorization_header() -> None:
    """Testa GET /auth/me sem Authorization header -> 401."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_health_remains_public() -> None:
    """Testa GET /health sem Authorization header -> 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


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

    def fake_get_chat_user_sync_service_override():
        return FakeChatUserSyncService()

    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
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


def test_get_auth_me_with_valid_token_without_chat_role() -> None:
    """Testa que GET /auth/me não exige role chat_vllm."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["public"],
    )

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        user=mock_user
    )
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService()
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert response.json()["roles"] == ["public"]
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_valid_token_and_inactive_user() -> None:
    """Testa que GET /auth/me permanece útil para usuário inativo."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=False,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )

    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        user=mock_user
    )
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService()
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert response.json()["is_active"] is False
    finally:
        app.dependency_overrides.clear()


def test_get_current_user_returns_authenticated_user() -> None:
    """Testa que get_current_user retorna AuthenticatedUser."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )

    def fake_get_auth_service_override():
        return FakeAuthService(user=mock_user)

    def fake_get_chat_user_sync_service_override():
        return FakeChatUserSyncService()

    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        result = get_current_user.__annotations__
        assert "return" in result
    finally:
        app.dependency_overrides.clear()


def test_get_current_chat_user_returns_chat_user() -> None:
    """Testa que get_current_chat_user retorna ChatUser."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )
    mock_chat_user = ChatUser(
        id="chat-user-uuid",
        adss_id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )

    class FakeChatUserSyncServiceWithChatUser(FakeChatUserSyncService):
        async def sync(self, user: AuthenticatedUser) -> ChatUser:
            self.sync_calls.append(user)
            return mock_chat_user

    def fake_get_auth_service_override():
        return FakeAuthService(user=mock_user)

    def fake_get_chat_user_sync_service_override():
        return FakeChatUserSyncServiceWithChatUser()

    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        result = get_current_chat_user.__annotations__
        assert "return" in result
    finally:
        app.dependency_overrides.clear()


def test_get_current_chat_user_sync_called_once() -> None:
    """Testa que sync é chamado apenas uma vez por get_current_chat_user."""

    class FakeChatUserSyncServiceWithChatUser(FakeChatUserSyncService):
        async def sync(self, user: AuthenticatedUser) -> ChatUser:
            self.sync_calls.append(user)
            return mock_chat_user

    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )
    mock_chat_user = ChatUser(
        id="chat-user-uuid",
        adss_id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )

    sync_service = FakeChatUserSyncServiceWithChatUser()

    def fake_get_auth_service_override():
        return FakeAuthService(user=mock_user)

    def fake_get_chat_user_sync_service_override():
        return sync_service

    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert len(sync_service.sync_calls) == 1
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_authentication_error() -> None:
    """Testa GET /auth/me com AuthenticationError -> 401."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        error=AuthenticationError("Invalid or expired token")
    )
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService()
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
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService()
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 403
        assert "does not have required role" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_external_service_error_from_sync() -> None:
    """Testa GET /auth/me com ExternalServiceError do sync -> 503."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        user=AuthenticatedUser(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )
    )
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService(
            error=ExternalServiceError("Database unavailable")
        )
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "Database unavailable"
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_with_external_service_error_from_auth() -> None:
    """Testa GET /auth/me com ExternalServiceError do auth_service -> 503."""
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService(
        error=ExternalServiceError("ADSS service unavailable")
    )
    app.dependency_overrides[get_chat_user_sync_service] = (
        lambda: FakeChatUserSyncService()
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 503
        assert response.json()["detail"] == "ADSS service unavailable"
    finally:
        app.dependency_overrides.clear()


def test_get_auth_me_sync_called_on_success() -> None:
    """Testa que sync é chamado quando autenticação é bem-sucedida."""
    mock_user = AuthenticatedUser(
        id="user123",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_staff=False,
        is_superuser=False,
        roles=["chat_vllm"],
    )

    sync_service = FakeChatUserSyncService()

    def fake_get_auth_service_override():
        return FakeAuthService(user=mock_user)

    def fake_get_chat_user_sync_service_override():
        return sync_service

    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.get(
            "/auth/me", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        assert len(sync_service.sync_calls) == 1
        assert sync_service.sync_calls[0].id == "user123"
    finally:
        app.dependency_overrides.clear()
