"""Cliente HTTP para o backend do labia-chat."""

import json
from collections.abc import Iterable, Iterator

import httpx


class CLIError(Exception):
    """Erro específico do CLI."""

    pass


class AuthError(CLIError):
    """Erro de autenticação (401)."""

    pass


class PermissionError(CLIError):
    """Erro de permissão (403)."""

    pass


class NotFoundError(CLIError):
    """Erro de recurso não encontrado (404)."""

    pass


class ValidationError(CLIError):
    """Erro de validação (422)."""

    pass


class BackendError(CLIError):
    """Erro no backend (502 ou outros)."""

    pass


class ConnectionError(CLIError):
    """Erro de conexão com o backend."""

    pass


CHAT_ACCESS_DENIED_MESSAGE = (
    "Acesso ao chat negado. Sua conta pode estar inativa ou sem a role chat_vllm."
)


class CLIClient:
    """Cliente HTTP para o backend do labia-chat."""

    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip("/")
        self.token: str | None = None
        self.conversation_id: str | None = None
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Obtém ou cria o cliente HTTP."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.api_url,
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                timeout=30.0,
            )
        return self._client

    def set_token(self, token: str) -> None:
        """Define o token de autenticação."""
        self.token = token
        if self._client is not None:
            self._client.headers["Authorization"] = f"Bearer {token}"

    def health_check(self) -> dict:
        """
        Verifica a saúde do backend via GET /health.

        Returns
        -------
        dict
            Dados retornados pelo endpoint de health.

        Raises
        ------
        BackendError
            Se o backend retornar erro ou payload inesperado.
        ConnectionError
            Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.get("/health")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            raise BackendError(
                f"Backend respondeu HTTP {exc.response.status_code} em /health."
            ) from exc
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def validate_token(self) -> dict:
        """
        Valida o token via GET /auth/me.

        Returns:
            dict: Dados do usuário autenticado.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.get("/auth/me")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def model_ping(self) -> dict:
        """
        Executa diagnóstico mínimo do modelo via POST /chat/model/ping.

        Returns
        -------
        dict
            Dados retornados pelo endpoint de ping do modelo.

        Raises
        ------
        AuthError
            Se o token for inválido (401).
        PermissionError
            Se o usuário não tiver permissão (403).
        ValidationError
            Se houver erro de validação (422).
        BackendError
            Se houver erro no backend ou payload inesperado.
        ConnectionError
            Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.post("/chat/model/ping", json={"prompt": "ping"})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code in (500, 502, 503):
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def create_conversation(self, title: str | None = None) -> dict:
        """
        Cria uma nova conversa via POST /chat/conversations.

        Args:
            title: Título opcional da conversa.

        Returns:
            dict: Dados da conversa criada.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        payload = {}
        if title:
            payload["title"] = title

        try:
            client = self._get_client()
            response = client.post("/chat/conversations", json=payload)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            self.conversation_id = data.get("id")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def list_conversations(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """
        Lista conversas do usuário via GET /chat/conversations.

        Args:
            limit: Número máximo de conversas a retornar (padrão: 20).
            offset: Número de conversas a pular (padrão: 0).

        Returns:
            list[dict]: Lista de conversas.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.get(
                "/chat/conversations", params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def list_messages(
        self, conversation_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """
        Lista mensagens de uma conversa via GET /chat/conversations/{id}/messages.

        Args:
            conversation_id: ID da conversa.
            limit: Número máximo de mensagens a retornar (padrão: 50).
            offset: Número de mensagens a pular (padrão: 0).

        Returns:
            list[dict]: Lista de mensagens.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            NotFoundError: Se a conversa não for encontrada (404).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.get(
                f"/chat/conversations/{conversation_id}/messages",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 404:
                raise NotFoundError("Conversa não encontrada para este usuário.")
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def get_conversation(self, conversation_id: str) -> dict:
        """
        Obtém uma conversa específica via GET /chat/conversations/{id}.

        Args:
            conversation_id: ID da conversa.

        Returns:
            dict: Dados da conversa.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            NotFoundError: Se a conversa não for encontrada (404).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        try:
            client = self._get_client()
            response = client.get(f"/chat/conversations/{conversation_id}")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 404:
                raise NotFoundError("Conversa não encontrada para este usuário.")
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def generate_message(self, content: str) -> dict:
        """
        Gera uma resposta do assistente via POST /chat/conversations/{id}/generate.

        Args:
            content: Conteúdo da mensagem do usuário.

        Returns:
            dict: Dados da mensagem do assistente gerada.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            NotFoundError: Se a conversa não for encontrada (404).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend (502).
            ConnectionError: Se não conseguir conectar ao backend.
        """
        if not self.conversation_id:
            raise CLIError("Nenhuma conversa selecionada. Crie uma conversa primeiro.")

        try:
            client = self._get_client()
            response = client.post(
                f"/chat/conversations/{self.conversation_id}/generate",
                json={"content": content},
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            if "content" not in data:
                raise BackendError("Resposta inesperada do backend. Tente novamente.")
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 404:
                raise NotFoundError("Conversa não encontrada para este usuário.")
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code == 502:
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    def stream_generate_message(self, content: str) -> Iterator[str]:
        """
        Streama uma resposta do assistente via endpoint SSE de geração.

        Args:
            content: Conteúdo da mensagem do usuário.

        Yields:
            Chunks de texto do assistente.

        Raises:
            AuthError: Se o token for inválido (401).
            PermissionError: Se o usuário não tiver permissão (403).
            NotFoundError: Se a conversa não for encontrada (404).
            ValidationError: Se houver erro de validação (422).
            BackendError: Se houver erro no backend ou evento SSE de erro.
            ConnectionError: Se não conseguir conectar ao backend.
        """
        if not self.conversation_id:
            raise CLIError("Nenhuma conversa selecionada. Crie uma conversa primeiro.")

        try:
            client = self._get_client()
            with client.stream(
                "POST",
                f"/chat/conversations/{self.conversation_id}/generate/stream",
                json={"content": content},
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()
                yield from self._iter_sse_text_chunks(response.iter_lines())
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise AuthError(
                    "Token inválido ou expirado. Gere um novo token AI-Scope."
                )
            elif exc.response.status_code == 403:
                raise PermissionError(CHAT_ACCESS_DENIED_MESSAGE)
            elif exc.response.status_code == 404:
                raise NotFoundError("Conversa não encontrada para este usuário.")
            elif exc.response.status_code == 422:
                raise ValidationError(
                    "Dados inválidos. Verifique a entrada e tente novamente."
                )
            elif exc.response.status_code in (500, 502):
                raise BackendError("Backend não conseguiu obter resposta do modelo.")
            raise
        except httpx.TimeoutException:
            raise ConnectionError("Timeout ao conectar ao backend. Tente novamente.")
        except httpx.NetworkError:
            raise ConnectionError("Falha de conexão com o backend. Verifique sua rede.")

    @classmethod
    def _iter_sse_text_chunks(cls, lines: Iterable[str]) -> Iterator[str]:
        for event_name, data in cls._iter_sse_events(lines):
            if event_name == "message":
                yield data
            elif event_name == "done":
                cls._parse_sse_control_json(data)
                return
            elif event_name == "error":
                payload = cls._parse_sse_control_json(data)
                detail = payload.get("detail", "Failed to generate response")
                raise BackendError(str(detail))

    @staticmethod
    def _iter_sse_events(lines: Iterable[str]) -> Iterator[tuple[str, str]]:
        event_name = "message"
        data_lines: list[str] = []

        def emit() -> tuple[str, str] | None:
            nonlocal event_name, data_lines
            if not data_lines and event_name == "message":
                return None
            event = (event_name, "\n".join(data_lines))
            event_name = "message"
            data_lines = []
            return event

        for raw_line in lines:
            line = raw_line.rstrip("\r")
            if line == "":
                event = emit()
                if event is not None:
                    yield event
                continue
            if line.startswith(":"):
                continue
            field, sep, value = line.partition(":")
            if not sep:
                continue
            if value.startswith(" "):
                value = value[1:]
            if field == "event":
                event_name = value
            elif field == "data":
                data_lines.append(value)

        event = emit()
        if event is not None:
            yield event

    @staticmethod
    def _parse_sse_control_json(data: str) -> dict:
        try:
            payload = json.loads(data) if data else {}
        except json.JSONDecodeError as exc:
            raise BackendError(
                "Resposta inesperada do backend. Tente novamente."
            ) from exc
        if not isinstance(payload, dict):
            raise BackendError("Resposta inesperada do backend. Tente novamente.")
        return payload

    def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client is not None:
            self._client.close()
            self._client = None
