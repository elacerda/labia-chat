"""Endpoint de chat para conversas e mensagens."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from labia_chat.api.deps import (
    get_chat_generation_service,
    get_chat_persistence_service,
    get_current_chat_user,
)
from labia_chat.models.user import ChatUser
from labia_chat.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    PingRequest,
    PingResponse,
)
from labia_chat.services.chat_generation import (
    ChatGenerationError,
    ChatGenerationService,
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
    conversation_id: UUID,
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
        conversation_id=str(conversation_id),
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
    conversation_id: UUID,
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
        conversation_id=str(conversation_id),
        user_id=chat_user.id,
    )
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada ou não pertence ao usuário",
        )
    return ConversationResponse.model_validate(conversation)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    conversation_id: UUID,
    payload: MessageCreate,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> MessageResponse:
    """
    Cria uma nova mensagem em uma conversa.

    Request:
        POST /chat/conversations/{conversation_id}/messages
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
        Body: { "role": "user", "content": "Mensagem", "model": null, "metadata": {} }

    Response:
        201 Created - MessageResponse criada
        400 Bad Request - Role inválido
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        503 Service Unavailable - Serviço externo indisponível
    """
    try:
        message = await service.add_message_for_user(
            conversation_id=str(conversation_id),
            user_id=chat_user.id,
            role=payload.role,
            content=payload.content,
            model=payload.model,
            metadata=payload.metadata,
        )
        return MessageResponse.model_validate(message)
    except ValueError as exc:
        error_msg = str(exc)
        if "Role inválido" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        elif "Conversa não encontrada ou não pertence ao usuário" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def list_messages(
    conversation_id: UUID,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
) -> list[MessageResponse]:
    """
    Lista mensagens de uma conversa.

    Request:
        GET /chat/conversations/{conversation_id}/messages
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - Lista de MessageResponse
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        503 Service Unavailable - Serviço externo indisponível
    """
    try:
        messages = await service.list_messages_for_user(
            conversation_id=str(conversation_id),
            user_id=chat_user.id,
        )
        return [MessageResponse.model_validate(m) for m in messages]
    except ValueError as exc:
        error_msg = str(exc)
        if "Conversa não encontrada ou não pertence ao usuário" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg,
            )


@router.post(
    "/model/ping",
    response_model=PingResponse,
    status_code=status.HTTP_200_OK,
    summary="Ping do modelo vLLM",
    description=(
        "Endpoint diagnóstico para validar geração mínima via vLLM, "
        "sem persistir nada."
    ),
)
async def model_ping(
    payload: PingRequest = PingRequest(),
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatGenerationService = Depends(get_chat_generation_service),
) -> PingResponse:
    """
    Endpoint diagnóstico para validar geração mínima via vLLM.

    Request:
        POST /chat/model/ping
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
        Body: { "prompt": "ping" } (opcional, default: "ping")

    Response:
        200 OK - PingResponse com a resposta do modelo
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        502 Bad Gateway - Falha na resposta/chamada do modelo vLLM
        503 Service Unavailable - Serviço externo indisponível

    Notas:
        - Não cria conversa
        - Não cria mensagem
        - Não persiste nada
        - Usa get_current_chat_user para autenticação
          como os endpoints /chat existentes
    """
    # Monta messages no formato OpenAI
    messages = [{"role": "user", "content": payload.prompt}]

    try:
        response_text = await service.generate(messages=messages)
    except ChatGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        ) from exc

    return PingResponse(response=response_text)

