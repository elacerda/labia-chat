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
