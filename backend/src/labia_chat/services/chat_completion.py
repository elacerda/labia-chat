"""Serviço de orquestração para geração persistente de resposta do assistente."""

from collections.abc import AsyncIterator
from typing import Optional

from labia_chat.services.chat_generation import (
    ChatGenerationError,
    ChatGenerationService,
)
from labia_chat.services.chat_persistence import ChatPersistenceService


class ChatCompletionError(Exception):
    """Erro durante a geração e persistência da resposta do assistente."""

    def __init__(self, message: str = "Failed to complete chat completion"):
        self.message = message
        super().__init__(self.message)


class ChatCompletionNotFoundError(ChatCompletionError):
    """Erro quando a conversa não é encontrada ou não pertence ao usuário."""

    def __init__(
        self,
        message: str = "Conversation not found or does not belong to user",
    ):
        self.message = message
        super().__init__(self.message)


class ChatCompletionGenerationError(ChatCompletionError):
    """Erro durante a geração da resposta pelo modelo."""

    def __init__(self, message: str = "Failed to generate response"):
        self.message = message
        super().__init__(self.message)


class ChatCompletionService:
    """
    Serviço de orquestração para geração persistente de resposta do assistente.

    Coordena:
    1. Validar/obter conversa do usuário
    2. Persistir mensagem user
    3. Listar histórico da conversa em ordem
    4. Converter histórico para formato OpenAI-compatible
    5. Chamar ChatGenerationService
    6. Persistir mensagem assistant com o texto gerado e o modelo configurado
    7. Retornar a mensagem assistant persistida

    Não depende de FastAPI e não levanta HTTPException.
    """

    def __init__(
        self,
        persistence_service: Optional[ChatPersistenceService] = None,
        generation_service: Optional[ChatGenerationService] = None,
    ):
        """
        Inicializa o serviço com services de persistência e geração.

        Args:
            persistence_service: Instância de ChatPersistenceService.
            generation_service: Instância de ChatGenerationService.
        """
        self.persistence_service = persistence_service or ChatPersistenceService()
        self.generation_service = generation_service or ChatGenerationService()

    async def complete(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        model: Optional[str] = None,
    ):
        """
        Completa uma resposta do assistente para uma conversa.

        Args:
            conversation_id: ID da conversa (string UUID).
            user_id: ID do usuário (string UUID).
            content: Conteúdo da mensagem do usuário.
            model: Nome do modelo a ser usado (opcional, usa default se não fornecido).

        Returns:
            ChatMessage: A mensagem assistant persistida com a resposta gerada.

        Raises:
            ChatCompletionError: Se a conversa não existir, não pertencer ao usuário,
                               ou se a geração falhar.
            ValueError: Se o conteúdo for vazio ou whitespace.
        """
        # Valida conteúdo não vazio
        if not content or not content.strip():
            raise ValueError("Content cannot be empty or whitespace only")

        # Valida/obtém conversa do usuário
        conversation = await self.persistence_service.get_conversation_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        if conversation is None:
            raise ChatCompletionNotFoundError(
                "Conversation not found or does not belong to user"
            )

        # Persiste mensagem user
        await self.persistence_service.add_message_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
            model=None,
            metadata=None,
        )

        # Lista histórico da conversa em ordem
        messages = await self.persistence_service.list_messages_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        # Converte histórico para formato OpenAI-compatible
        openai_messages = [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

        # Chama ChatGenerationService
        try:
            response_text = await self.generation_service.generate(openai_messages)
        except ChatGenerationError as exc:
            # Propaga erro de geração como erro do novo service
            # Mantém a mensagem user persistida conforme especificado
            raise ChatCompletionGenerationError(
                f"Failed to generate response: {exc.message}"
            ) from exc

        # Persiste mensagem assistant com o texto gerado e o modelo configurado
        assistant_message = await self.persistence_service.add_message_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
            role="assistant",
            content=response_text,
            model=model,
            metadata=None,
        )

        return assistant_message

    async def complete_stream(
        self,
        conversation_id: str,
        user_id: str,
        content: str,
        model: Optional[str] = None,
    ) -> AsyncIterator[tuple[str, str | None]]:
        """
        Prepara e streama uma resposta do assistente para uma conversa.

        Yields:
            ("text", chunk) para deltas de texto.
            ("done", message_id) após persistir a mensagem assistant.
        """
        if not content or not content.strip():
            raise ValueError("Content cannot be empty or whitespace only")

        conversation = await self.persistence_service.get_conversation_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        if conversation is None:
            raise ChatCompletionNotFoundError(
                "Conversation not found or does not belong to user"
            )

        await self.persistence_service.add_message_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
            role="user",
            content=content,
            model=None,
            metadata=None,
        )

        messages = await self.persistence_service.list_messages_for_user(
            conversation_id=conversation_id,
            user_id=user_id,
        )

        openai_messages = [
            {"role": message.role, "content": message.content}
            for message in messages
        ]

        async def stream_events() -> AsyncIterator[tuple[str, str | None]]:
            response_chunks: list[str] = []
            try:
                async for chunk in self.generation_service.generate_stream(
                    openai_messages
                ):
                    response_chunks.append(chunk)
                    yield "text", chunk
            except ChatGenerationError as exc:
                raise ChatCompletionGenerationError(
                    "Failed to generate response"
                ) from exc

            response_text = "".join(response_chunks)
            assistant_message = await self.persistence_service.add_message_for_user(
                conversation_id=conversation_id,
                user_id=user_id,
                role="assistant",
                content=response_text,
                model=model,
                metadata=None,
            )
            message_id = getattr(assistant_message, "id", None)
            yield "done", str(message_id) if message_id is not None else None

        return stream_events()
