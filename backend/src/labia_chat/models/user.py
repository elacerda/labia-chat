"""Modelo SQLAlchemy para usuário do labia-chat."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from labia_chat.db.base import Base


def utc_now() -> datetime:
    """Retorna datetime UTC aware."""
    return datetime.now(UTC)


class ChatUser(Base):
    """Usuário local do labia-chat vinculado ao usuário do AI-Scope/ADSS.

    Mantém duas identidades:
    - id: UUID interno do labia-chat (primary key)
    - adss_id: UUID externo do AI-Scope/ADSS (único, não é primary key)
    """

    __tablename__ = "chat_users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    adss_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    username: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
    )

    is_staff: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    is_superuser: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    roles: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("adss_id", name="uq_chat_users_adss_id"),
        Index("ix_chat_users_username", "username"),
        Index("ix_chat_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<ChatUser(id={self.id!r}, username={self.username!r})>"
