"""Schemas Pydantic para chat (conversas e mensagens)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    """Schema para criação de nova conversa."""

    title: str | None = None
    metadata: dict[str, Any] | None = None


class ConversationResponse(BaseModel):
    """Schema de resposta para conversa (pública)."""

    id: UUID
    title: str | None
    metadata: dict[str, Any] = Field(
        alias="conversation_metadata", serialization_alias="metadata"
    )
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MessageCreate(BaseModel):
    """Schema para criação de nova mensagem."""

    role: str
    content: str
    model: str | None = None
    metadata: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    """Schema de resposta para mensagem (pública)."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    sequence_index: int
    model: str | None
    metadata: dict[str, Any] = Field(
        alias="message_metadata", serialization_alias="metadata"
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PingRequest(BaseModel):
    """Schema para requisição de ping (diagnóstico de geração)."""

    prompt: str = "ping"


class PingResponse(BaseModel):
    """Schema para resposta de ping (diagnóstico de geração)."""

    response: str
