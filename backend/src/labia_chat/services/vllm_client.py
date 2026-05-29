"""Cliente HTTP para o servidor vLLM OpenAI-compatible."""

import asyncio
import json
from collections.abc import AsyncIterator
from http import HTTPStatus

import httpx

from labia_chat.core.config import settings


class VLLMClientError(Exception):
    """Erro do cliente vLLM: timeout, falha de rede ou resposta inválida."""

    def __init__(self, message: str = "vLLM service is unavailable"):
        self.message = message
        self.status_code = HTTPStatus.SERVICE_UNAVAILABLE
        super().__init__(self.message)


class VLLMClient:
    """Cliente para comunicação com o servidor vLLM OpenAI-compatible."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        api_key: str | None = None,
    ):
        """
        Inicializa o cliente vLLM.

        Args:
            base_url: URL base do vLLM. Se não fornecida, usa settings.vllm_base_url.
            model: Nome do modelo a ser usado. Se não fornecido, usa
                settings.vllm_model.
            timeout: Timeout em segundos para requisições. Se não fornecido, usa
                settings.vllm_timeout_seconds.
            api_key: API key para autenticação. Se não fornecida ou vazia, não envia
                Authorization header.
        """
        self.base_url = (base_url or settings.vllm_base_url).rstrip("/")
        self.model = model or settings.vllm_model
        self.timeout = timeout or settings.vllm_timeout_seconds
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "VLLMClient":
        """Entrar no contexto assíncrono."""
        headers = {"Content-Type": "application/json"}
        if self._api_key and self._api_key.strip():
            headers["Authorization"] = f"Bearer {self._api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Sair do contexto assíncrono."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> str:
        """
        Gera uma resposta usando o modelo vLLM.

        Args:
            messages: Lista de mensagens no formato OpenAI.
                      Cada mensagem deve ter 'role' e 'content'.
            temperature: Temperatura para geração (0.0 a 1.0).
            max_tokens: Número máximo de tokens a gerar.

        Returns:
            O conteúdo textual da resposta do modelo.

        Raises:
            VLLMClientError: Se houver erro de rede, timeout ou resposta inválida.
        """
        if not self._client:
            raise RuntimeError("VLLMClient must be used as async context manager")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self._client.post(
                "/v1/chat/completions",
                json=payload,
            )
        except asyncio.TimeoutError as exc:
            raise VLLMClientError(
                f"Request to vLLM timed out after {self.timeout}s"
            ) from exc
        except httpx.RequestError as exc:
            raise VLLMClientError(f"Failed to connect to vLLM: {exc}") from exc

        # Tratar erros HTTP
        if response.status_code != HTTPStatus.OK:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get(
                    "message", "Unknown error"
                )
            except Exception:
                error_message = response.text
            raise VLLMClientError(
                f"vLLM returned status {response.status_code}: {error_message}"
            )

        # Validar e extrair resposta
        try:
            response_data = response.json()
        except Exception as exc:
            raise VLLMClientError("Failed to parse vLLM response as JSON") from exc

        # Validar estrutura mínima da resposta
        if "choices" not in response_data:
            raise VLLMClientError("vLLM response missing 'choices' field")

        choices = response_data["choices"]
        if not isinstance(choices, list) or len(choices) == 0:
            raise VLLMClientError("vLLM response 'choices' is empty or not a list")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise VLLMClientError("vLLM first choice is not a dictionary")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise VLLMClientError("vLLM first choice message is not a dictionary")

        content = message.get("content")
        if content is None:
            raise VLLMClientError("vLLM first choice message missing 'content' field")

        if not isinstance(content, str):
            raise VLLMClientError("vLLM first choice message content is not a string")

        return content

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 32,
    ) -> AsyncIterator[str]:
        """
        Stream a response using the OpenAI-compatible vLLM chat completions API.

        Yields choices[].delta.content strings, preserving whitespace-only chunks.
        """
        if not self._client:
            raise RuntimeError("VLLMClient must be used as async context manager")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self._client.stream(
                "POST",
                "/v1/chat/completions",
                json=payload,
            ) as response:
                if response.status_code != HTTPStatus.OK:
                    raise VLLMClientError(
                        f"vLLM streaming returned status {response.status_code}"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data = line.removeprefix("data:").strip()
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError as exc:
                        raise VLLMClientError(
                            "Failed to parse vLLM streaming response as JSON"
                        ) from exc

                    for text in self._extract_stream_text_deltas(chunk):
                        yield text
        except asyncio.TimeoutError as exc:
            raise VLLMClientError(
                f"Streaming request to vLLM timed out after {self.timeout}s"
            ) from exc
        except httpx.RequestError as exc:
            raise VLLMClientError("Failed to connect to vLLM stream") from exc

    @staticmethod
    def _extract_stream_text_deltas(chunk: dict) -> list[str]:
        """Extract choices[].delta.content strings from a stream chunk."""
        if "choices" not in chunk:
            raise VLLMClientError("vLLM stream chunk missing 'choices' field")

        choices = chunk["choices"]
        if not isinstance(choices, list):
            raise VLLMClientError("vLLM stream chunk 'choices' is not a list")

        text_deltas: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                raise VLLMClientError("vLLM stream choice is not a dictionary")

            delta = choice.get("delta")
            if delta is None:
                continue
            if not isinstance(delta, dict):
                raise VLLMClientError("vLLM stream choice delta is not a dictionary")

            content = delta.get("content")
            if content is None or content == "":
                continue
            if not isinstance(content, str):
                raise VLLMClientError(
                    "vLLM stream choice delta content is not a string"
                )
            text_deltas.append(content)

        return text_deltas
