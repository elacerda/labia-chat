"""Modelo SQLAlchemy para usuário do labia-chat."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Relações
    conversations: Mapped[list["ChatConversation"]] = relationship(
        "ChatConversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("adss_id", name="uq_chat_users_adss_id"),
        Index("ix_chat_users_username", "username"),
        Index("ix_chat_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<ChatUser(id={self.id!r}, username={self.username!r})>"


class ChatConversation(Base):
    """Conversa entre usuário e o sistema.

    Cada conversa pertence a um único usuário (ChatUser) e pode conter
    múltiplas mensagens (ChatMessage).
    """

    __tablename__ = "chat_conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_users.id", ondelete="CASCADE"),
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    conversation_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
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

    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relações
    user: Mapped[ChatUser] = relationship(
        "ChatUser",
        back_populates="conversations",
    )

    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.sequence_index",
    )

    __table_args__ = (
        Index("ix_chat_conversations_user_id", "user_id"),
        Index("ix_chat_conversations_created_at", "created_at"),
        Index("ix_chat_conversations_archived_at", "archived_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatConversation(id={self.id!r}, title={self.title!r})>"


class ChatMessage(Base):
    """Mensagem de uma conversa.

    Pode ser do tipo:
    - "user": mensagem do usuário
    - "assistant": resposta do sistema
    - "system": mensagem do sistema (não exibida ao usuário)
    - "tool": resposta de ferramenta
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    sequence_index: Mapped[int] = mapped_column(
        nullable=False,
    )

    model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relações
    conversation: Mapped[ChatConversation] = relationship(
        "ChatConversation",
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_chat_messages_conversation_id", "conversation_id"),
        Index("ix_chat_messages_created_at", "created_at"),
        UniqueConstraint(
            "conversation_id",
            "sequence_index",
            name="uq_chat_messages_conversation_sequence",
        ),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id!r}, role={self.role!r})>"

