"""Endpoint de chat para conversas."""

from fastapi import APIRouter, Depends, HTTPException, status

from labia_chat.api.deps import (
    get_chat_persistence_service,
    get_current_chat_user,
)
from labia_chat.models.user import ChatUser
from labia_chat.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
)
from labia_chat.services.chat_persistence import ChatPersistenceService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> list[ConversationResponse]:
    """
    Lista conversas do usuário autenticado.

    Request:
        GET /chat/conversations
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - Lista de ConversationResponse
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        503 Service Unavailable - Serviço externo indisponível
    """
    conversations = await service.list_conversations_for_user(chat_user.id)
    return [ConversationResponse.model_validate(c) for c in conversations]


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> ConversationResponse:
    """
    Cria uma nova conversa.

    Request:
        POST /chat/conversations
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
        Body: { "title": "Título", "metadata": {} }

    Response:
        201 Created - ConversationResponse criada
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        503 Service Unavailable - Serviço externo indisponível
    """
    conversation = await service.create_conversation(
        user_id=chat_user.id,
        title=payload.title,
        metadata=payload.metadata,
    )
    return ConversationResponse.model_validate(conversation)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_conversation(
    conversation_id: str,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> ConversationResponse:
    """
    Obtém uma conversa específica pelo ID.

    Request:
        GET /chat/conversations/{conversation_id}
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - ConversationResponse
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        503 Service Unavailable - Serviço externo indisponível
    """
    conversation = await service.get_conversation_for_user(
        conversation_id=conversation_id,
        user_id=chat_user.id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada ou não pertence ao usuário",
        )
    return ConversationResponse.model_validate(conversation)


@router.post(
    "/conversations/{conversation_id}/archive",
    response_model=ConversationResponse,
)
async def archive_conversation(
    conversation_id: str,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> ConversationResponse:
    """
    Arquiva uma conversa pertencente ao usuário.

    Request:
        POST /chat/conversations/{conversation_id}/archive
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - ConversationResponse arquivada
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        503 Service Unavailable - Serviço externo indisponível
    """
    conversation = await service.archive_conversation_for_user(
        conversation_id=conversation_id,
        user_id=chat_user.id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada ou não pertence ao usuário",
        )
    return ConversationResponse.model_validate(conversation)
