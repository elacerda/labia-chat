"""Cliente HTTP para o backend do labia-chat."""

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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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

    def list_conversations(self) -> list[dict]:
        """
        Lista conversas do usuário via GET /chat/conversations.

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
            response = client.get("/chat/conversations")
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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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

    def list_messages(self, conversation_id: str) -> list[dict]:
        """
        Lista mensagens de uma conversa via GET /chat/conversations/{id}/messages.

        Args:
            conversation_id: ID da conversa.

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
            response = client.get(f"/chat/conversations/{conversation_id}/messages")
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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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
                raise PermissionError(
                    "Usuário autenticado, mas sem permissão chat_vllm."
                )
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

    def close(self) -> None:
        """Fecha o cliente HTTP."""
        if self._client is not None:
            self._client.close()
            self._client = None
