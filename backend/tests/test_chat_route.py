"""Testes de integração HTTP para o endpoint /chat/conversations."""

from uuid import uuid4

from fastapi.testclient import TestClient

from labia_chat.api.deps import (
    get_chat_persistence_service,
    get_current_chat_user,
)
from labia_chat.main import app

client = TestClient(app)


class FakeChatUser:
    """Fake de ChatUser para testes (não acessa banco real)."""

    def __init__(self, id: str, adss_id: str, username: str = "testuser"):
        self.id = id
        self.adss_id = adss_id
        self.username = username
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.is_active = True
        self.is_staff = False
        self.is_superuser = False
        self.roles = ["chat_vllm"]


class FakeChatPersistenceService:
    """Fake de ChatPersistenceService para testes (não acessa banco real)."""

    def __init__(self):
        self.conversations: list = []
        self.create_calls: list = []
        self.list_calls: list = []

    def create_conversation_sync(
        self, user_id: str, title: str | None = None, metadata: dict | None = None
    ):
        """Simula criação de conversa (versão síncrona para testes)."""
        self.create_calls.append(
            {"user_id": user_id, "title": title, "metadata": metadata}
        )
        from datetime import datetime

        conv = type(
            "ChatConversation",
            (),
            {
                "id": uuid4(),
                "user_id": user_id,
                "title": title,
                "conversation_metadata": metadata or {},
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "archived_at": None,
            },
        )()
        self.conversations.append(conv)
        return conv

    async def create_conversation(
        self, user_id: str, title: str | None = None, metadata: dict | None = None
    ):
        """Simula criação de conversa."""
        return self.create_conversation_sync(user_id, title, metadata)

    async def list_conversations_for_user(
        self, user_id: str, include_archived: bool = False
    ):
        """Simula listagem de conversas."""
        self.list_calls.append(
            {"user_id": user_id, "include_archived": include_archived}
        )
        return [
            c
            for c in self.conversations
            if c.user_id == user_id and (include_archived or c.archived_at is None)
        ]


def test_get_conversations_without_authorization() -> None:
    """Testa GET /chat/conversations sem Authorization -> 401."""
    response = client.get("/chat/conversations")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_conversations_with_valid_user() -> None:
    """Testa GET /chat/conversations com usuário autenticado -> 200."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        response = client.get(
            "/chat/conversations", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    finally:
        app.dependency_overrides.clear()


def test_get_conversations_uses_chat_user_id_internal() -> None:
    """Testa que GET usa chat_user.id interno, não adss_id."""
    internal_id = str(uuid4())
    adss_id = "adss-user-123"
    fake_user = FakeChatUser(id=internal_id, adss_id=adss_id)
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        client.get(
            "/chat/conversations", headers={"Authorization": "Bearer valid-token"}
        )
        # Verifica que list_calls foi feita com o id interno, não adss_id
        assert len(fake_service.list_calls) == 1
        assert fake_service.list_calls[0]["user_id"] == internal_id
        assert fake_service.list_calls[0]["user_id"] != adss_id
    finally:
        app.dependency_overrides.clear()


def test_post_conversation_without_authorization() -> None:
    """Testa POST /chat/conversations sem Authorization -> 401."""
    response = client.post(
        "/chat/conversations",
        json={"title": "Test Conversation", "metadata": {"key": "value"}},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_post_conversation_creates_with_correct_data() -> None:
    """Testa POST /chat/conversations cria conversa com dados corretos."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {
            "title": "Test Conversation",
            "metadata": {"key": "value", "nested": {"key": "value"}},
        }
        response = client.post(
            "/chat/conversations",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Conversation"
        assert data["metadata"] == {"key": "value", "nested": {"key": "value"}}
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "archived_at" in data

        # Verifica que o service recebeu os dados corretos
        assert len(fake_service.create_calls) == 1
        call = fake_service.create_calls[0]
        assert call["user_id"] == fake_user.id
        assert call["title"] == "Test Conversation"
        assert call["metadata"] == {"key": "value", "nested": {"key": "value"}}
    finally:
        app.dependency_overrides.clear()


def test_post_conversation_with_title_only() -> None:
    """Testa POST /chat/conversations com título apenas."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"title": "Only Title"}
        response = client.post(
            "/chat/conversations",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Only Title"
        assert data["metadata"] == {}
    finally:
        app.dependency_overrides.clear()


def test_post_conversation_with_empty_metadata() -> None:
    """Testa POST /chat/conversations com metadata vazio."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"title": "Test", "metadata": {}}
        response = client.post(
            "/chat/conversations",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["metadata"] == {}
    finally:
        app.dependency_overrides.clear()


def test_post_conversation_without_title() -> None:
    """Testa POST /chat/conversations sem título (title=None)."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"metadata": {"key": "value"}}
        response = client.post(
            "/chat/conversations",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None
    finally:
        app.dependency_overrides.clear()


def test_get_conversations_returns_fake_with_metadata() -> None:
    """Testa GET /chat/conversations com conversa fake e valida estrutura."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-456")
    fake_service = FakeChatPersistenceService()

    # Cria uma conversa fake para o usuário (versão síncrona)
    fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={"key": "value", "nested": {"key": "value"}},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_persistence_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        response = client.get(
            "/chat/conversations", headers={"Authorization": "Bearer valid-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        # Verifica que metadata vem de conversation_metadata
        assert data[0]["metadata"] == {"key": "value", "nested": {"key": "value"}}
        # Verifica que user_id não aparece na resposta pública
        assert "user_id" not in data[0]
    finally:
        app.dependency_overrides.clear()

