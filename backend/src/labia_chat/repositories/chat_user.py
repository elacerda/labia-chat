"""Repositório para sincronização de usuário ChatUser."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from labia_chat.models.user import ChatUser, utc_now
from labia_chat.schemas.user import AuthenticatedUser


class ChatUserRepository:
    """Repositório para operações de sincronização de usuário."""

    async def upsert(self, session: AsyncSession, user: AuthenticatedUser) -> ChatUser:
        """
        Faz upsert de usuário por adss_id.

        Args:
            session: Sessão async do SQLAlchemy.
            user: AuthenticatedUser com dados do ADSS.

        Returns:
            ChatUser: Instância do usuário (criado ou atualizado).
        """
        # Convert user.id to UUID
        adss_id = uuid.UUID(user.id)

        stmt = select(ChatUser).where(ChatUser.adss_id == adss_id)
        result = await session.scalar(stmt)

        if result is not None:
            # Atualiza campos mutáveis
            result.username = user.username
            result.email = user.email
            result.full_name = user.full_name
            result.is_active = user.is_active
            result.is_staff = user.is_staff
            result.is_superuser = user.is_superuser
            result.roles = user.roles
            # Atualiza last_seen_at em cada sincronização
            result.last_seen_at = utc_now()
            return result

        # Cria novo usuário
        new_user = ChatUser(
            adss_id=adss_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
            roles=user.roles,
            last_seen_at=utc_now(),
        )
        session.add(new_user)
        return new_user
