"""Testes de sincronização de usuário ChatUserSyncService."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from labia_chat.core.errors import ExternalServiceError
from labia_chat.schemas.user import AuthenticatedUser
from labia_chat.services.chat_user_sync import ChatUserSyncService


class FakeChatUserRepository:
    """Fake de ChatUserRepository para testes."""

    def __init__(self, users=None, error=None):
        self.users = users or {}
        self.error = error
        self.upsert_calls = []

    async def upsert(self, session, user: AuthenticatedUser):
        """Simula upsert."""
        self.upsert_calls.append((session, user))
        if self.error:
            raise self.error
        # Retorna um ChatUser fake
        return MagicMock(id=uuid.uuid4(), adss_id=user.id)


@asynccontextmanager
async def fake_session_scope(session: MagicMock):
    """Fake session scope para testes usando asynccontextmanager."""
    yield session


class TestChatUserSyncService:
    """Testes para ChatUserSyncService."""

    @pytest.mark.asyncio
    async def test_sync_creates_user_successfully(self):
        """Testa que sync cria usuário quando não existe."""
        fake_repo = FakeChatUserRepository()
        fake_session = MagicMock(spec=AsyncSession)

        sync_service = ChatUserSyncService(
            repository=fake_repo,
            session_scope_factory=lambda: fake_session_scope(fake_session),
        )

        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )

        await sync_service.sync(user)
        assert len(fake_repo.upsert_calls) == 1
        assert fake_repo.upsert_calls[0][1].username == "testuser"

    @pytest.mark.asyncio
    async def test_sync_updates_existing_user(self):
        """Testa que sync atualiza usuário existente."""
        fake_repo = FakeChatUserRepository()
        fake_session = MagicMock(spec=AsyncSession)

        sync_service = ChatUserSyncService(
            repository=fake_repo,
            session_scope_factory=lambda: fake_session_scope(fake_session),
        )

        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="updated_user",
            email="updated@example.com",
            full_name="Updated User",
            is_active=True,
            is_staff=True,
            is_superuser=False,
            roles=["chat_vllm", "admin"],
        )

        await sync_service.sync(user)
        assert len(fake_repo.upsert_calls) == 1
        assert fake_repo.upsert_calls[0][1].username == "updated_user"

    @pytest.mark.asyncio
    async def test_sync_fails_on_repository_error(self):
        """Testa que sync levanta ExternalServiceError se repository falhar."""
        fake_repo = FakeChatUserRepository(
            error=Exception("Database connection failed")
        )
        fake_session = MagicMock(spec=AsyncSession)

        sync_service = ChatUserSyncService(
            repository=fake_repo,
            session_scope_factory=lambda: fake_session_scope(fake_session),
        )

        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )

        with pytest.raises(ExternalServiceError) as exc_info:
            await sync_service.sync(user)
        assert "Database connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sync_with_custom_repository(self):
        """Testa que sync usa repository customizado."""
        custom_repo = MagicMock()
        custom_repo.upsert = AsyncMock()
        fake_session = MagicMock(spec=AsyncSession)

        sync_service = ChatUserSyncService(
            repository=custom_repo,
            session_scope_factory=lambda: fake_session_scope(fake_session),
        )
        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )

        await sync_service.sync(user)
        custom_repo.upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_uses_custom_session_scope_factory(self):
        """Testa que sync usa session_scope_factory customizada."""
        fake_repo = FakeChatUserRepository()
        custom_session = MagicMock(spec=AsyncSession)

        session_scope_called = False

        @asynccontextmanager
        async def custom_session_scope():
            nonlocal session_scope_called
            session_scope_called = True
            yield custom_session

        sync_service = ChatUserSyncService(
            repository=fake_repo,
            session_scope_factory=custom_session_scope,
        )
        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )

        await sync_service.sync(user)
        assert session_scope_called is True
        assert len(fake_repo.upsert_calls) == 1
        assert fake_repo.upsert_calls[0][0] == custom_session

    @pytest.mark.asyncio
    async def test_sync_does_not_connect_to_real_database(self):
        """Testa que sync não conecta no banco real."""
        fake_repo = FakeChatUserRepository()
        fake_session = MagicMock(spec=AsyncSession)

        sync_service = ChatUserSyncService(
            repository=fake_repo,
            session_scope_factory=lambda: fake_session_scope(fake_session),
        )
        user = AuthenticatedUser(
            id=str(uuid.uuid4()),
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            is_active=True,
            is_staff=False,
            is_superuser=False,
            roles=["chat_vllm"],
        )

        await sync_service.sync(user)
        # Verifica que a sessão fake foi usada (não há conexão real)
        # A sessão fake não deve ter commit/close chamados porque o fake_session_scope
        # não os chama - isso é responsabilidade do session_scope real
        assert fake_session.commit.call_count == 0
        assert fake_session.close.call_count == 0
