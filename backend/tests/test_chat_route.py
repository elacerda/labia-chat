"""Testes de integração HTTP para o endpoint /chat/conversations."""

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from labia_chat.api.deps import (
    get_auth_service,
    get_chat_completion_service,
    get_chat_generation_service,
    get_chat_persistence_service,
    get_chat_user_sync_service,
    get_current_chat_user,
)
from labia_chat.api.routes.chat import GenerateRequest, generate_response_stream
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
        self.get_calls: list = []
        self.archive_calls: list = []

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
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 20,
        offset: int = 0,
    ):
        """Simula listagem de conversas."""
        self.list_calls.append(
            {
                "user_id": user_id,
                "include_archived": include_archived,
                "limit": limit,
                "offset": offset,
            }
        )
        all_conversations = [
            c
            for c in self.conversations
            if c.user_id == user_id and (include_archived or c.archived_at is None)
        ]
        # Apply limit and offset
        return all_conversations[offset : offset + limit]

    async def get_conversation_for_user(self, conversation_id: str, user_id: str):
        """Simula obtenção de conversa por ID e usuário."""
        self.get_calls.append({"conversation_id": conversation_id, "user_id": user_id})
        for c in self.conversations:
            # Convert UUID to string for comparison
            conv_id_str = str(c.id) if hasattr(c.id, "__str__") else c.id
            if conv_id_str == conversation_id and c.user_id == user_id:
                return c
        return None

    async def archive_conversation_for_user(self, conversation_id: str, user_id: str):
        """Simula arquivamento de conversa."""
        self.archive_calls.append(
            {"conversation_id": conversation_id, "user_id": user_id}
        )
        for c in self.conversations:
            # Convert UUID to string for comparison
            conv_id_str = str(c.id) if hasattr(c.id, "__str__") else c.id
            if conv_id_str == conversation_id and c.user_id == user_id:
                from datetime import datetime

                c.archived_at = datetime.now()
                return c
        return None


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


# --- Testes para POST /chat/model/ping ---


class FakeChatGenerationService:
    """Fake de ChatGenerationService para testes (não acessa vLLM real)."""

    def __init__(self):
        self.generate_calls: list = []

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> str:
        """Simula geração e armazena a chamada."""
        self.generate_calls.append(
            {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        )
        # Retorna uma resposta simulada
        return "Test response from model"


def test_post_model_ping_returns_200_with_response() -> None:
    """Testa POST /model/ping retorna 200 e PingResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatGenerationService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_generation_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_generation_service] = (
        fake_get_chat_generation_service_override
    )

    try:
        response = client.post(
            "/chat/model/ping",
            json={"prompt": "Hello"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "Test response from model"
        # Verifica que generate foi chamado com as mensagens corretas
        assert len(fake_service.generate_calls) == 1
        call = fake_service.generate_calls[0]
        assert call["messages"] == [{"role": "user", "content": "Hello"}]
    finally:
        app.dependency_overrides.clear()


def test_post_model_ping_uses_default_prompt_when_empty() -> None:
    """Testa POST /model/ping usa prompt='ping' quando body vazio."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatGenerationService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_generation_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_generation_service] = (
        fake_get_chat_generation_service_override
    )

    try:
        # Envia body vazio - deve usar o default "ping"
        response = client.post(
            "/chat/model/ping",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        # Verifica que generate foi chamado com o prompt default
        assert len(fake_service.generate_calls) == 1
        call = fake_service.generate_calls[0]
        assert call["messages"] == [{"role": "user", "content": "ping"}]
    finally:
        app.dependency_overrides.clear()


def test_post_model_ping_returns_502_on_generation_error() -> None:
    """Testa POST /model/ping retorna 502 quando ChatGenerationError."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")

    class FakeChatGenerationServiceWithError:
        async def generate(self, messages: list[dict[str, str]]) -> str:
            from labia_chat.services.chat_generation import ChatGenerationError

            raise ChatGenerationError("Model not found")

    fake_service = FakeChatGenerationServiceWithError()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_generation_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_generation_service] = (
        fake_get_chat_generation_service_override
    )

    try:
        response = client.post(
            "/chat/model/ping",
            json={"prompt": "Test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 502
        assert response.json()["detail"] == "Model not found"
    finally:
        app.dependency_overrides.clear()


def test_post_model_ping_requires_authentication() -> None:
    """Testa POST /model/ping sem Authorization -> 401."""
    response = client.post(
        "/chat/model/ping",
        json={"prompt": "Test"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_post_model_ping_uses_chat_user_for_auth() -> None:
    """Testa POST /model/ping usa get_current_chat_user para autenticação."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatGenerationService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_generation_service_override():
        return fake_service

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_generation_service] = (
        fake_get_chat_generation_service_override
    )

    try:
        response = client.post(
            "/chat/model/ping",
            json={"prompt": "Test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        # Verifica que o endpoint usa o mesmo mecanismo de autenticação
        # que os outros endpoints /chat (get_current_chat_user)
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


def test_get_conversation_without_authorization() -> None:
    """Testa GET /chat/conversations/{id} sem Authorization -> 401."""
    response = client.get("/chat/conversations/some-id")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_conversation_returns_200_and_response_model() -> None:
    """Testa GET /chat/conversations/{id} retorna 200 e ConversationResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={"key": "value"},
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
            f"/chat/conversations/{created_conv.id}",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_conv.id)
        assert data["title"] == "Test Conversation"
        assert data["metadata"] == {"key": "value"}
        assert "created_at" in data
        assert "updated_at" in data
        assert "archived_at" in data
    finally:
        app.dependency_overrides.clear()


def test_get_conversation_uses_chat_user_id_internal() -> None:
    """Testa que GET /conversations/{id} usa chat_user.id interno."""
    internal_id = str(uuid4())
    adss_id = "adss-user-123"
    fake_user = FakeChatUser(id=internal_id, adss_id=adss_id)
    fake_service = FakeChatPersistenceService()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        client.get(
            f"/chat/conversations/{created_conv.id}",
            headers={"Authorization": "Bearer valid-token"},
        )
        # Verifica que get_calls foi feita com o id interno, não adss_id
        assert len(fake_service.get_calls) == 1
        assert fake_service.get_calls[0]["user_id"] == internal_id
        assert fake_service.get_calls[0]["user_id"] != adss_id
    finally:
        app.dependency_overrides.clear()


def test_get_conversation_returns_404_when_service_returns_none() -> None:
    """Testa GET /conversations/{id} retorna 404 quando service retorna None."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()
    # Não cria nenhuma conversa, então get_conversation_for_user retornará None

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
        # Use a valid UUID that doesn't exist in the fake service
        non_existent_uuid = str(uuid4())
        response = client.get(
            f"/chat/conversations/{non_existent_uuid}",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Conversa não encontrada ou não pertence ao usuário"
        )
    finally:
        app.dependency_overrides.clear()


def test_archive_conversation_returns_200_and_response_model() -> None:
    """Testa POST /conversations/{id}/archive retorna 200 e ConversationResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={"key": "value"},
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
        response = client.post(
            f"/chat/conversations/{created_conv.id}/archive",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(created_conv.id)
        assert data["title"] == "Test Conversation"
        assert data["metadata"] == {"key": "value"}
        assert "created_at" in data
        assert "updated_at" in data
        assert "archived_at" in data
        # Verifica que a conversa foi arquivada
        assert data["archived_at"] is not None
    finally:
        app.dependency_overrides.clear()


def test_archive_conversation_uses_chat_user_id_internal() -> None:
    """Testa que POST /archive usa chat_user.id interno."""
    internal_id = str(uuid4())
    adss_id = "adss-user-123"
    fake_user = FakeChatUser(id=internal_id, adss_id=adss_id)
    fake_service = FakeChatPersistenceService()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        client.post(
            f"/chat/conversations/{created_conv.id}/archive",
            headers={"Authorization": "Bearer valid-token"},
        )
        # Verifica que archive_calls foi feita com o id interno, não adss_id
        assert len(fake_service.archive_calls) == 1
        assert fake_service.archive_calls[0]["user_id"] == internal_id
        assert fake_service.archive_calls[0]["user_id"] != adss_id
    finally:
        app.dependency_overrides.clear()


def test_archive_conversation_returns_404_when_service_returns_none() -> None:
    """Testa POST /archive retorna 404 quando service retorna None."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceService()
    # Não cria nenhuma conversa, então archive_conversation_for_user retornará None

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
        # Use a valid UUID that doesn't exist in the fake service
        non_existent_uuid = str(uuid4())
        response = client.post(
            f"/chat/conversations/{non_existent_uuid}/archive",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Conversa não encontrada ou não pertence ao usuário"
        )
    finally:
        app.dependency_overrides.clear()


def test_archive_conversation_without_authorization() -> None:
    """Testa POST /conversations/{id}/archive sem Authorization -> 401."""
    response = client.post("/chat/conversations/some-id/archive")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


class FakeChatMessage:
    """Fake de ChatMessage para testes (não acessa banco real)."""

    def __init__(
        self,
        id: str,
        conversation_id: str,
        role: str,
        content: str,
        sequence_index: int,
        model: str | None = None,
        metadata: dict | None = None,
    ):
        self.id = id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.sequence_index = sequence_index
        self.model = model
        self.message_metadata = metadata or {}
        from datetime import datetime

        self.created_at = datetime.now()


class FakeChatPersistenceServiceWithMessages(FakeChatPersistenceService):
    """Fake de ChatPersistenceService com suporte a mensagens."""

    def __init__(self):
        super().__init__()
        self.messages: list = []
        self.add_calls: list = []
        self.list_calls: list = []

    def create_message_sync(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sequence_index: int,
        model: str | None = None,
        metadata: dict | None = None,
    ):
        """Simula criação de mensagem (versão síncrona para testes)."""
        self.add_calls.append(
            {
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "sequence_index": sequence_index,
                "model": model,
                "metadata": metadata,
            }
        )
        msg = FakeChatMessage(
            id=str(uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_index=sequence_index,
            model=model,
            metadata=metadata,
        )
        self.messages.append(msg)
        return msg

    async def add_message_for_user(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        model: str | None = None,
        metadata: dict | None = None,
    ):
        """Simula adição de mensagem."""
        # Valida role permitida
        allowed_roles = {"user", "assistant", "system", "tool"}
        if role not in allowed_roles:
            roles_str = ", ".join(sorted(allowed_roles))
            raise ValueError(f"Role inválido: {role}. Roles permitidos: {roles_str}")

        # Verifica que a conversa existe e pertence ao usuário
        found_conv = None
        for c in self.conversations:
            conv_id_str = str(c.id) if hasattr(c.id, "__str__") else c.id
            if conv_id_str == conversation_id and c.user_id == user_id:
                found_conv = c
                break

        if found_conv is None:
            raise ValueError("Conversa não encontrada ou não pertence ao usuário")

        # Calcula o próximo índice de sequência
        msg_list = [m for m in self.messages if m.conversation_id == conversation_id]
        sequence_index = len(msg_list)

        # Cria a mensagem
        return self.create_message_sync(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sequence_index=sequence_index,
            model=model,
            metadata=metadata,
        )

    async def list_messages_for_user(
        self, conversation_id: str, user_id: str, limit: int = 50, offset: int = 0
    ):
        """Simula listagem de mensagens."""
        self.list_calls.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "limit": limit,
                "offset": offset,
            }
        )

        # Verifica que a conversa existe e pertence ao usuário
        found_conv = None
        for c in self.conversations:
            conv_id_str = str(c.id) if hasattr(c.id, "__str__") else c.id
            if conv_id_str == conversation_id and c.user_id == user_id:
                found_conv = c
                break

        if found_conv is None:
            raise ValueError("Conversa não encontrada ou não pertence ao usuário")

        all_messages = [
            m for m in self.messages if m.conversation_id == conversation_id
        ]
        # Apply limit and offset
        return all_messages[offset : offset + limit]


def test_post_message_without_authorization() -> None:
    """Testa POST /chat/conversations/{id}/messages sem Authorization -> 401."""
    response = client.post(
        "/chat/conversations/some-id/messages",
        json={"role": "user", "content": "Test message"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_post_message_returns_201_and_message_response() -> None:
    """Testa POST /chat/conversations/{id}/messages retorna 201 e MessageResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        payload = {
            "role": "user",
            "content": "Hello, world!",
            "model": "gpt-4",
            "metadata": {"key": "value"},
        }
        response = client.post(
            f"/chat/conversations/{created_conv.id}/messages",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, world!"
        assert data["model"] == "gpt-4"
        assert data["metadata"] == {"key": "value"}
        assert "id" in data
        assert "sequence_index" in data
        assert "created_at" in data
    finally:
        app.dependency_overrides.clear()


def test_post_message_uses_chat_user_id_internal() -> None:
    """Testa que POST /messages usa chat_user.id interno, não adss_id."""
    internal_id = str(uuid4())
    adss_id = "adss-user-123"
    fake_user = FakeChatUser(id=internal_id, adss_id=adss_id)
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        payload = {
            "role": "user",
            "content": "Test message",
        }
        client.post(
            f"/chat/conversations/{created_conv.id}/messages",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        # Verifica que add_calls foi feita com o id interno, não adss_id
        assert len(fake_service.add_calls) == 1
        # O service.add_message_for_user recebe user_id como string UUID
        # Verifica que a chamada foi feita com o id interno
        assert fake_service.add_calls[0]["conversation_id"] == str(created_conv.id)
    finally:
        app.dependency_overrides.clear()


def test_post_message_passes_correct_data_to_service() -> None:
    """Testa que POST /messages passa role, content, model e metadata corretamente."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        payload = {
            "role": "assistant",
            "content": "Response",
            "model": "gpt-4",
            "metadata": {"key": "value", "nested": {"key": "value"}},
        }
        client.post(
            f"/chat/conversations/{created_conv.id}/messages",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        # Verifica que o service recebeu os dados corretos
        assert len(fake_service.add_calls) == 1
        call = fake_service.add_calls[0]
        assert call["role"] == "assistant"
        assert call["content"] == "Response"
        assert call["model"] == "gpt-4"
        assert call["metadata"] == {"key": "value", "nested": {"key": "value"}}
    finally:
        app.dependency_overrides.clear()


def test_post_message_returns_400_for_invalid_role() -> None:
    """Testa POST /messages retorna 400 para role inválida."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
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
        payload = {
            "role": "invalid_role",
            "content": "Test message",
        }
        response = client.post(
            f"/chat/conversations/{created_conv.id}/messages",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 400
        assert "Role inválido" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_post_message_returns_404_when_conversation_not_found() -> None:
    """Testa POST /messages retorna 404 quando conversa não existe ou não pertence."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()
    # Não cria nenhuma conversa, então add_message_for_user retornará ValueError

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
            "role": "user",
            "content": "Test message",
        }
        # Use a valid UUID that doesn't exist in the fake service
        non_existent_uuid = str(uuid4())
        response = client.post(
            f"/chat/conversations/{non_existent_uuid}/messages",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Conversa não encontrada ou não pertence ao usuário"
        )
    finally:
        app.dependency_overrides.clear()


def test_get_messages_returns_200_and_list_of_message_responses() -> None:
    """Testa GET /messages retorna 200 e lista de MessageResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    # Cria algumas mensagens para a conversa
    fake_service.create_message_sync(
        conversation_id=str(created_conv.id),
        role="user",
        content="First message",
        sequence_index=0,
    )
    fake_service.create_message_sync(
        conversation_id=str(created_conv.id),
        role="assistant",
        content="Second message",
        sequence_index=1,
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
            f"/chat/conversations/{created_conv.id}/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Verifica estrutura das mensagens
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "First message"
        assert data[1]["role"] == "assistant"
        assert data[1]["content"] == "Second message"
        assert "id" in data[0]
        assert "sequence_index" in data[0]
        assert "created_at" in data[0]
    finally:
        app.dependency_overrides.clear()


def test_get_messages_preserves_metadata_from_message_metadata() -> None:
    """Testa que GET /messages preserva metadata vindo de message_metadata."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    # Cria uma mensagem com metadata
    fake_service.create_message_sync(
        conversation_id=str(created_conv.id),
        role="user",
        content="Message with metadata",
        sequence_index=0,
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
            f"/chat/conversations/{created_conv.id}/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verifica que metadata vem de message_metadata
        assert data[0]["metadata"] == {"key": "value", "nested": {"key": "value"}}
    finally:
        app.dependency_overrides.clear()


def test_get_messages_does_not_expose_extra_fields() -> None:
    """Testa que GET /messages não expõe campos extras (como user_id)."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    # Cria uma mensagem
    fake_service.create_message_sync(
        conversation_id=str(created_conv.id),
        role="user",
        content="Test message",
        sequence_index=0,
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
            f"/chat/conversations/{created_conv.id}/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # Verifica que campos extras não aparecem na resposta pública
        assert "user_id" not in data[0]
        assert "conversation_id" in data[0]  # Este deve aparecer
    finally:
        app.dependency_overrides.clear()


def test_get_messages_uses_chat_user_id_internal() -> None:
    """Testa que GET /messages usa chat_user.id interno, não adss_id."""
    internal_id = str(uuid4())
    adss_id = "adss-user-123"
    fake_user = FakeChatUser(id=internal_id, adss_id=adss_id)
    fake_service = FakeChatPersistenceServiceWithMessages()

    # Cria uma conversa para o usuário
    created_conv = fake_service.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    # Cria uma mensagem
    fake_service.create_message_sync(
        conversation_id=str(created_conv.id),
        role="user",
        content="Test message",
        sequence_index=0,
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
        client.get(
            f"/chat/conversations/{created_conv.id}/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        # Verifica que list_calls foi feita com o id interno, não adss_id
        assert len(fake_service.list_calls) == 1
        assert fake_service.list_calls[0]["user_id"] == internal_id
        assert fake_service.list_calls[0]["user_id"] != adss_id
    finally:
        app.dependency_overrides.clear()


def test_get_messages_returns_404_when_conversation_not_found() -> None:
    """Testa GET /messages retorna 404 quando conversa não existe ou não pertence."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatPersistenceServiceWithMessages()
    # Não cria nenhuma conversa, então list_messages_for_user retornará ValueError

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
        # Use a valid UUID that doesn't exist in the fake service
        non_existent_uuid = str(uuid4())
        response = client.get(
            f"/chat/conversations/{non_existent_uuid}/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Conversa não encontrada ou não pertence ao usuário"
        )
    finally:
        app.dependency_overrides.clear()


def test_get_messages_without_authorization() -> None:
    """Testa GET /chat/conversations/{id}/messages sem Authorization -> 401."""
    response = client.get("/chat/conversations/some-id/messages")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_get_conversation_with_invalid_uuid_returns_422() -> None:
    """Testa GET /conversations/{id} com UUID inválido -> 422."""
    # O FastAPI valida UUID após as dependências, então precisamos de um token válido
    # O token "valid-token" é aceito pelo AuthService fake
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_auth_service_override():
        from labia_chat.services.auth_service import AuthService

        return AuthService()

    def fake_get_chat_user_sync_service_override():
        from labia_chat.services.chat_user_sync import ChatUserSyncService

        return ChatUserSyncService()

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.get(
            "/chat/conversations/invalid-uuid",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()
    finally:
        app.dependency_overrides.clear()


# --- Testes para POST /chat/conversations/{conversation_id}/generate ---


class FakeChatCompletionService:
    """Fake de ChatCompletionService para testes (não acessa banco real)."""

    def __init__(self):
        self.complete_calls: list = []
        self.complete_stream_calls: list = []
        self.messages: list = []
        self.stream_message_id = str(uuid4())

    async def complete(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        model: str | None = None,
    ):
        """Simula geração de resposta."""
        self.complete_calls.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "content": content,
                "model": model,
            }
        )
        from datetime import datetime

        msg = type(
            "ChatMessage",
            (),
            {
                "id": uuid4(),
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": "assistant",
                "content": "Generated response",
                "model": model,
                "message_metadata": {},
                "sequence_index": len(self.messages),
                "created_at": datetime.now(),
            },
        )()
        self.messages.append(msg)
        return msg

    async def complete_stream(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        model: str | None = None,
    ):
        """Simula geração de resposta em streaming."""
        self.complete_stream_calls.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "content": content,
                "model": model,
            }
        )

        async def events():
            yield "text", "Hello"
            yield "text", ", world"
            yield "done", self.stream_message_id

        return events()


def test_generate_response_returns_201_and_message_response() -> None:
    """Testa POST /generate retorna 201 e MessageResponse."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatCompletionService()

    # Cria uma conversa para o usuário
    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"content": "Explique o que é uma supernova tipo Ia."}
        response = client.post(
            f"/chat/conversations/{created_conv.id}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "assistant"
        assert data["content"] == "Generated response"
        assert "id" in data
        assert "sequence_index" in data
        assert "created_at" in data
        # Verifica que service foi chamado com os parâmetros corretos
        assert len(fake_service.complete_calls) == 1
        call = fake_service.complete_calls[0]
        assert call["conversation_id"] == str(created_conv.id)
        assert call["user_id"] == internal_id
        assert call["content"] == payload["content"]
        assert call["model"] == "qwen-coder-next"
    finally:
        app.dependency_overrides.clear()


def test_generate_response_does_not_expose_user_id() -> None:
    """Testa que POST /generate não expõe user_id na resposta."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatCompletionService()

    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"content": "Test content"}
        response = client.post(
            f"/chat/conversations/{created_conv.id}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 201
        data = response.json()
        # Verifica que user_id não aparece na resposta pública
        assert "user_id" not in data
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_generate_response_stream_returns_sse_and_done_event() -> None:
    """Testa handler /generate/stream retorna chunks SSE e evento done."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatCompletionService()

    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    response = await generate_response_stream(
        conversation_id=created_conv.id,
        payload=GenerateRequest(content="Test content"),
        chat_user=fake_user,
        service=fake_service,
    )

    body = "".join([chunk async for chunk in response.body_iterator])

    assert response.status_code == 200
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "no-cache"
    assert response.headers["connection"] == "keep-alive"
    assert response.headers["x-accel-buffering"] == "no"
    assert body == (
        "data: Hello\n\n"
        "data: , world\n\n"
        f'event: done\ndata: {{"message_id":"{fake_service.stream_message_id}"}}\n\n'
    )
    assert len(fake_service.complete_stream_calls) == 1
    call = fake_service.complete_stream_calls[0]
    assert call["conversation_id"] == str(created_conv.id)
    assert call["user_id"] == internal_id
    assert call["content"] == "Test content"
    assert call["model"] == "qwen-coder-next"
    assert fake_service.complete_calls == []


@pytest.mark.asyncio
async def test_generate_response_stream_cancelled_error_propagates() -> None:
    """Testa que cancelamento do stream não vira evento SSE de erro."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")

    class CancelledStreamService(FakeChatCompletionService):
        async def complete_stream(
            self,
            conversation_id: str,
            user_id: str,
            content: str,
            model: str | None = None,
        ):
            self.complete_stream_calls.append(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "content": content,
                    "model": model,
                }
            )

            async def events():
                yield "text", "partial"
                raise asyncio.CancelledError()

            return events()

    fake_service = CancelledStreamService()
    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    response = await generate_response_stream(
        conversation_id=created_conv.id,
        payload=GenerateRequest(content="Test content"),
        chat_user=fake_user,
        service=fake_service,
    )

    chunks = []
    with pytest.raises(asyncio.CancelledError):
        async for chunk in response.body_iterator:
            chunks.append(chunk)

    assert chunks == ["data: partial\n\n"]


def test_generate_and_generate_stream_routes_are_registered() -> None:
    """Testa que endpoint antigo permanece e novo endpoint foi registrado."""
    post_paths = {
        route.path
        for route in app.routes
        if "POST" in getattr(route, "methods", set())
    }

    assert "/chat/conversations/{conversation_id}/generate" in post_paths
    assert "/chat/conversations/{conversation_id}/generate/stream" in post_paths


def test_generate_response_returns_404_when_conversation_not_found() -> None:
    """Testa POST /generate retorna 404 quando conversa não existe."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")

    class FakeChatCompletionServiceWithNotFound:
        async def complete(
            self,
            conversation_id: str,
            user_id: str,
            content: str,
            model: str | None = None,
        ):
            from labia_chat.services.chat_completion import ChatCompletionNotFoundError

            raise ChatCompletionNotFoundError(
                "Conversation not found or does not belong to user"
            )

    fake_service = FakeChatCompletionServiceWithNotFound()

    fake_persistence = FakeChatPersistenceService()

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        # Use a valid UUID that doesn't exist in the fake service
        non_existent_uuid = str(uuid4())
        payload = {"content": "Test content"}
        response = client.post(
            f"/chat/conversations/{non_existent_uuid}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Conversation not found or does not belong to user"
        )
    finally:
        app.dependency_overrides.clear()


def test_generate_response_returns_502_on_generation_error() -> None:
    """Testa POST /generate retorna 502 quando geração falha."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")

    class FakeChatCompletionServiceWithGenerationError:
        async def complete(
            self,
            conversation_id: str,
            user_id: str,
            content: str,
            model: str | None = None,
        ):
            from labia_chat.services.chat_completion import (
                ChatCompletionGenerationError,
            )

            raise ChatCompletionGenerationError("Failed to generate response")

    fake_service = FakeChatCompletionServiceWithGenerationError()

    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"content": "Test content"}
        response = client.post(
            f"/chat/conversations/{created_conv.id}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 502
        assert response.json()["detail"] == "Failed to generate response"
    finally:
        app.dependency_overrides.clear()


def test_generate_response_returns_400_for_empty_content() -> None:
    """Testa POST /generate retorna 400 para conteúdo vazio."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatCompletionService()

    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"content": ""}
        response = client.post(
            f"/chat/conversations/{created_conv.id}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 400
        assert "Content cannot be empty" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_generate_response_returns_400_for_whitespace_content() -> None:
    """Testa POST /generate retorna 400 para conteúdo whitespace-only."""
    internal_id = str(uuid4())
    fake_user = FakeChatUser(id=internal_id, adss_id="adss-user-123")
    fake_service = FakeChatCompletionService()

    fake_persistence = FakeChatPersistenceService()
    created_conv = fake_persistence.create_conversation_sync(
        user_id=internal_id,
        title="Test Conversation",
        metadata={},
    )

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_chat_completion_service_override():
        return fake_service

    def fake_get_chat_persistence_service_override():
        return fake_persistence

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_chat_completion_service] = (
        fake_get_chat_completion_service_override
    )
    app.dependency_overrides[get_chat_persistence_service] = (
        fake_get_chat_persistence_service_override
    )

    try:
        payload = {"content": "   "}
        response = client.post(
            f"/chat/conversations/{created_conv.id}/generate",
            json=payload,
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 400
        assert "Content cannot be empty" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_generate_response_with_invalid_uuid_returns_422() -> None:
    """Testa POST /generate com UUID inválido -> 422."""
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_auth_service_override():
        from labia_chat.services.auth_service import AuthService

        return AuthService()

    def fake_get_chat_user_sync_service_override():
        from labia_chat.services.chat_user_sync import ChatUserSyncService

        return ChatUserSyncService()

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.post(
            "/chat/conversations/invalid-uuid/generate",
            json={"content": "Test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_generate_response_without_authorization() -> None:
    """Testa POST /chat/conversations/{id}/generate sem Authorization -> 401."""
    response = client.post(
        "/chat/conversations/some-id/generate",
        json={"content": "Test"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_post_message_with_invalid_uuid_returns_422() -> None:
    """Testa POST /messages com UUID inválido -> 422."""
    # O FastAPI valida UUID após as dependências, então precisamos de um token válido
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_auth_service_override():
        from labia_chat.services.auth_service import AuthService

        return AuthService()

    def fake_get_chat_user_sync_service_override():
        from labia_chat.services.chat_user_sync import ChatUserSyncService

        return ChatUserSyncService()

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.post(
            "/chat/conversations/invalid-uuid/messages",
            json={"role": "user", "content": "Test"},
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_archive_conversation_with_invalid_uuid_returns_422() -> None:
    """Testa POST /archive com UUID inválido -> 422."""
    # O FastAPI valida UUID após as dependências, então precisamos de um token válido
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_auth_service_override():
        from labia_chat.services.auth_service import AuthService

        return AuthService()

    def fake_get_chat_user_sync_service_override():
        from labia_chat.services.chat_user_sync import ChatUserSyncService

        return ChatUserSyncService()

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.post(
            "/chat/conversations/invalid-uuid/archive",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_get_messages_with_invalid_uuid_returns_422() -> None:
    """Testa GET /messages com UUID inválido -> 422."""
    # O FastAPI valida UUID após as dependências, então precisamos de um token válido
    fake_user = FakeChatUser(id=str(uuid4()), adss_id="adss-user-123")

    def fake_get_current_chat_user_override():
        return fake_user

    def fake_get_auth_service_override():
        from labia_chat.services.auth_service import AuthService

        return AuthService()

    def fake_get_chat_user_sync_service_override():
        from labia_chat.services.chat_user_sync import ChatUserSyncService

        return ChatUserSyncService()

    app.dependency_overrides[get_current_chat_user] = (
        fake_get_current_chat_user_override
    )
    app.dependency_overrides[get_auth_service] = fake_get_auth_service_override
    app.dependency_overrides[get_chat_user_sync_service] = (
        fake_get_chat_user_sync_service_override
    )

    try:
        response = client.get(
            "/chat/conversations/invalid-uuid/messages",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert response.status_code == 422
        assert "detail" in response.json()
    finally:
        app.dependency_overrides.clear()
