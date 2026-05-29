"""Endpoint de chat para conversas e mensagens."""

import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from labia_chat.api.deps import (
    get_chat_completion_service,
    get_chat_generation_service,
    get_chat_persistence_service,
    get_current_chat_user,
)
from labia_chat.api.sse import sse_json_event, sse_text
from labia_chat.core.config import settings
from labia_chat.models.user import ChatUser
from labia_chat.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
    PingRequest,
    PingResponse,
)
from labia_chat.services.chat_completion import (
    ChatCompletionGenerationError,
    ChatCompletionNotFoundError,
    ChatCompletionService,
)
from labia_chat.services.chat_generation import (
    ChatGenerationError,
    ChatGenerationService,
)
from labia_chat.services.chat_persistence import ChatPersistenceService

router = APIRouter(prefix="/chat", tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatPersistenceService = Depends(get_chat_persistence_service),
    limit: int = Query(
        default=20, ge=1, le=100, description="Número máximo de conversas a retornar"
    ),
    offset: int = Query(default=0, ge=0, description="Número de conversas a pular"),
) -> list[ConversationResponse]:
    """
    Lista conversas do usuário autenticado.

    Request:
        GET /chat/conversations?limit=20&offset=0
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - Lista de ConversationResponse
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        422 Unprocessable Entity - Parâmetros inválidos
        503 Service Unavailable - Serviço externo indisponível
    """
    conversations = await service.list_conversations_for_user(
        chat_user.id, limit=limit, offset=offset
    )
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
    limit: int = Query(
        default=50, ge=1, le=200, description="Número máximo de mensagens a retornar"
    ),
    offset: int = Query(default=0, ge=0, description="Número de mensagens a pular"),
) -> list[MessageResponse]:
    """
    Lista mensagens de uma conversa.

    Request:
        GET /chat/conversations/{conversation_id}/messages?limit=50&offset=0
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>

    Response:
        200 OK - Lista de MessageResponse
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        422 Unprocessable Entity - Parâmetros inválidos
        503 Service Unavailable - Serviço externo indisponível
    """
    try:
        messages = await service.list_messages_for_user(
            conversation_id=str(conversation_id),
            user_id=chat_user.id,
            limit=limit,
            offset=offset,
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
        "Endpoint diagnóstico para validar geração mínima via vLLM, sem persistir nada."
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


class GenerateRequest(BaseModel):
    """Schema para requisição de geração de resposta."""

    content: str


@router.post(
    "/conversations/{conversation_id}/generate",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Geração persistente de resposta",
    description=(
        "Gera resposta do assistente para uma conversa existente, "
        "persistindo tanto a mensagem do usuário quanto a resposta do assistente."
    ),
)
async def generate_response(
    conversation_id: UUID,
    payload: GenerateRequest,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatCompletionService = Depends(get_chat_completion_service),
) -> MessageResponse:
    """
    Gera resposta do assistente para uma conversa existente.

    Request:
        POST /chat/conversations/{conversation_id}/generate
        Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
        Body: { "content": "Mensagem do usuário" }

    Response:
        201 Created - MessageResponse da mensagem assistant persistida
        400 Bad Request - Conteúdo vazio ou whitespace
        401 Unauthorized - Token inválido ou ausente
        403 Forbidden - Usuário sem permissão
        404 Not Found - Conversa não encontrada ou não pertence ao usuário
        422 Unprocessable Entity - UUID inválido no path
        502 Bad Gateway - Falha na geração da resposta pelo modelo

    Notas:
        - Autentica usuário via get_current_chat_user
        - Valida que conversa pertence ao usuário
        - Persiste mensagem user
        - Chama geração via vLLM
        - Persiste mensagem assistant com model configurado
        - Retorna MessageResponse da mensagem assistant
    """
    # Valida que content não está vazio ou whitespace
    if not payload.content or payload.content.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content cannot be empty",
        )

    try:
        result = await service.complete(
            conversation_id=str(conversation_id),
            user_id=chat_user.id,
            content=payload.content,
            model=settings.vllm_model,
        )
        return MessageResponse.model_validate(result)
    except ChatCompletionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except ChatCompletionGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        error_msg = str(exc)
        if "Content cannot be empty" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )


@router.post(
    "/conversations/{conversation_id}/generate/stream",
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
    summary="Geração persistente de resposta em streaming",
    description=(
        "Gera resposta do assistente para uma conversa existente via SSE, "
        "persistindo a resposta do assistente apenas após conclusão bem-sucedida."
    ),
)
async def generate_response_stream(
    conversation_id: UUID,
    payload: GenerateRequest,
    chat_user: ChatUser = Depends(get_current_chat_user),
    service: ChatCompletionService = Depends(get_chat_completion_service),
) -> StreamingResponse:
    """Streama resposta do assistente para uma conversa existente."""
    if not payload.content or payload.content.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content cannot be empty",
        )

    try:
        stream_events = await service.complete_stream(
            conversation_id=str(conversation_id),
            user_id=chat_user.id,
            content=payload.content,
            model=settings.vllm_model,
        )
    except ChatCompletionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    async def event_source() -> AsyncIterator[str]:
        try:
            async for event_type, data in stream_events:
                if event_type == "text":
                    yield sse_text(data or "")
                elif event_type == "done":
                    payload = {"message_id": data} if data is not None else {}
                    yield sse_json_event(payload, event="done")
        except ChatCompletionGenerationError:
            yield sse_json_event(
                {"detail": "Failed to generate response"},
                event="error",
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            yield sse_json_event(
                {"detail": "Failed to generate response"},
                event="error",
            )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
