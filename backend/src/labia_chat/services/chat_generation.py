"""Serviço de geração de chat usando VLLM."""

from typing import Optional

from labia_chat.services.vllm_client import VLLMClient, VLLMClientError


class ChatGenerationError(Exception):
    """Erro durante a geração de chat com VLLM."""

    def __init__(self, message: str = "Failed to generate chat response"):
        self.message = message
        super().__init__(self.message)


class ChatGenerationService:
    """
    Serviço de geração de chat usando VLLM.

    Responsável por:
    - Validar mensagens de entrada
    - Chamar o VLLMClient
    - Retornar o texto da resposta do assistant

    Não persiste nada, não conhece FastAPI diretamente e não cria endpoints.
    """

    # Roles permitidas seguindo o padrão do projeto (chat_persistence.py)
    ALLOWED_ROLES = {"user", "assistant", "system", "tool"}

    def __init__(
        self,
        vllm_client: Optional[VLLMClient] = None,
    ):
        """
        Inicializa o serviço com VLLMClient.

        Args:
            vllm_client: Instância de VLLMClient. Se não fornecida, cria uma nova.
        """
        self.vllm_client = vllm_client or VLLMClient()

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> str:
        """
        Gera uma resposta usando o modelo VLLM.

        Args:
            messages: Lista de mensagens no formato OpenAI.
                      Cada mensagem deve ter 'role' e 'content'.
            temperature: Temperatura para geração (0.0 a 1.0).
            max_tokens: Número máximo de tokens a gerar.

        Returns:
            O conteúdo textual da resposta do modelo.

        Raises:
            ChatGenerationError: Se messages for inválido ou VLLM falhar.
        """
        # Valida messages
        self._validate_messages(messages)

        # Chama o VLLMClient
        try:
            return await self.vllm_client.generate(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except VLLMClientError as exc:
            raise ChatGenerationError(
                f"VLLM failed to generate response: {exc.message}"
            ) from exc

    def _validate_messages(self, messages: list[dict[str, str]]) -> None:
        """
        Valida a lista de mensagens.

        Args:
            messages: Lista de mensagens a ser validada.

        Raises:
            ChatGenerationError: Se a validação falhar.
        """
        # messages não pode ser vazio
        if not messages:
            raise ChatGenerationError("messages cannot be empty")

        for i, msg in enumerate(messages):
            # Cada item deve ser dict
            if not isinstance(msg, dict):
                raise ChatGenerationError(
                    f"messages[{i}] must be a dictionary, got {type(msg).__name__}"
                )

            # Cada item deve ter 'role'
            if "role" not in msg:
                raise ChatGenerationError(
                    f"messages[{i}] must have 'role' key"
                )

            # Cada item deve ter 'content'
            if "content" not in msg:
                raise ChatGenerationError(
                    f"messages[{i}] must have 'content' key"
                )

            role = msg.get("role")
            content = msg.get("content")

            # role deve ser string
            if not isinstance(role, str):
                raise ChatGenerationError(
                    f"messages[{i}]['role'] must be a string, got {type(role).__name__}"
                )

            # content deve ser string não vazia
            if not isinstance(content, str):
                raise ChatGenerationError(
                    f"messages[{i}]['content'] must be a string, "
                    f"got {type(content).__name__}"
                )

            if not content.strip():
                raise ChatGenerationError(
                    f"messages[{i}]['content'] cannot be empty or whitespace only"
                )

            # role permitida deve seguir o contrato do projeto
            if role not in self.ALLOWED_ROLES:
                roles_str = ", ".join(sorted(self.ALLOWED_ROLES))
                raise ChatGenerationError(
                    f"Invalid role: {role}. Allowed roles: {roles_str}"
                )
