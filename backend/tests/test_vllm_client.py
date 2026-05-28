"""Testes unitários para o VLLMClient."""

from http import HTTPStatus

import pytest

from labia_chat.core.config import settings
from labia_chat.services.vllm_client import VLLMClient, VLLMClientError


class FakeAsyncHTTPClient:
    """Fake de httpx.AsyncClient para testes sem rede."""

    def __init__(self, base_url: str, timeout: float):
        self.base_url = base_url
        self.timeout = timeout
        self.last_request = None
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def post(
        self, path: str, json: dict | None = None, headers: dict | None = None
    ):
        """Simula POST e armazena a requisição."""
        self.call_count += 1
        self.last_request = {
            "path": path,
            "json": json,
            "headers": headers,
        }
        return self._response

    def set_success_response(self, content: str = "Test response"):
        """Configura uma resposta de sucesso."""
        self._response = FakeHTTPResponse(
            status_code=HTTPStatus.OK,
            json_data={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": content,
                        }
                    }
                ]
            },
        )

    def set_error_response(self, status_code: int, error_message: str = "Error"):
        """Configura uma resposta de erro."""
        self._response = FakeHTTPResponse(
            status_code=status_code,
            json_data={"error": {"message": error_message}},
        )

    def set_no_choices_response(self):
        """Configura uma resposta sem choices."""
        self._response = FakeHTTPResponse(
            status_code=HTTPStatus.OK,
            json_data={"other_field": "value"},
        )

    def set_empty_choices_response(self):
        """Configura uma resposta com choices vazio."""
        self._response = FakeHTTPResponse(
            status_code=HTTPStatus.OK,
            json_data={"choices": []},
        )

    def set_no_content_response(self):
        """Configura uma resposta sem content no message."""
        self._response = FakeHTTPResponse(
            status_code=HTTPStatus.OK,
            json_data={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                        }
                    }
                ]
            },
        )


class FakeHTTPResponse:
    """Fake de httpx.Response para testes."""

    def __init__(self, status_code: int, json_data: dict):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data

    @property
    def text(self) -> str:
        return str(self._json_data)


@pytest.fixture
def vllm_client():
    """Cria um VLLMClient com configuração de teste."""
    return VLLMClient(
        base_url="http://localhost:8000",
        model="test-model",
        timeout=30.0,
    )


class TestVLLMClient:
    """Testes para VLLMClient."""

    @pytest.mark.asyncio
    async def test_generate_success(self, vllm_client):
        """Testa chamada bem-sucedida com resposta válida."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_success_response("Hello, world!")

        # Mock do httpx.AsyncClient
        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            result = await vllm_client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.0,
                max_tokens=32,
            )

            assert result == "Hello, world!"
            assert fake_http.call_count == 1
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_generate_payload_structure(self, vllm_client):
        """Testa que o payload enviado tem a estrutura correta."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_success_response("Response")

        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            await vllm_client.generate(
                messages=[{"role": "user", "content": "Test"}],
                temperature=0.5,
                max_tokens=100,
            )

            assert fake_http.last_request["path"] == "/v1/chat/completions"
            assert fake_http.last_request["json"]["model"] == "test-model"
            assert fake_http.last_request["json"]["messages"] == [
                {"role": "user", "content": "Test"}
            ]
            assert fake_http.last_request["json"]["temperature"] == 0.5
            assert fake_http.last_request["json"]["max_tokens"] == 100
            assert (
                fake_http.last_request["headers"]["Content-Type"]
                == "application/json"
            )
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_generate_http_error(self, vllm_client):
        """Testa tratamento de erro HTTP."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_error_response(HTTPStatus.BAD_REQUEST, "Invalid request")

        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            with pytest.raises(VLLMClientError) as exc_info:
                await vllm_client.generate(
                    messages=[{"role": "user", "content": "Test"}]
                )

            assert "400" in str(exc_info.value)
            assert "Invalid request" in str(exc_info.value)
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_generate_no_choices(self, vllm_client):
        """Testa tratamento de resposta sem choices."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_no_choices_response()

        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            with pytest.raises(VLLMClientError) as exc_info:
                await vllm_client.generate(
                    messages=[{"role": "user", "content": "Test"}]
                )

            assert "choices" in str(exc_info.value)
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_generate_empty_choices(self, vllm_client):
        """Testa tratamento de choices vazio."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_empty_choices_response()

        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            with pytest.raises(VLLMClientError) as exc_info:
                await vllm_client.generate(
                    messages=[{"role": "user", "content": "Test"}]
                )

            assert (
                "empty" in str(exc_info.value) or "choices" in str(exc_info.value)
            )
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_generate_no_content(self, vllm_client):
        """Testa tratamento de resposta sem content no message."""
        fake_http = FakeAsyncHTTPClient(base_url="", timeout=0)
        fake_http.set_no_content_response()

        original_client = vllm_client._client
        vllm_client._client = fake_http

        try:
            with pytest.raises(VLLMClientError) as exc_info:
                await vllm_client.generate(
                    messages=[{"role": "user", "content": "Test"}]
                )

            assert "content" in str(exc_info.value)
        finally:
            vllm_client._client = original_client

    @pytest.mark.asyncio
    async def test_context_manager(self, vllm_client):
        """Testa uso como context manager."""
        async with VLLMClient(
            base_url="http://localhost:8000",
            model="test-model",
            timeout=30.0,
        ) as client:
            assert client._client is not None

        # Após sair do contexto, o client deve ser None
        assert client._client is None

    @pytest.mark.asyncio
    async def test_generate_without_context_manager_raises_error(self, vllm_client):
        """Testa que generate levanta erro se não usado como context manager."""
        with pytest.raises(RuntimeError) as exc_info:
            await vllm_client.generate(
                messages=[{"role": "user", "content": "Test"}]
            )

        assert "must be used as async context manager" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_default_values_from_settings(self):
        """Testa que valores padrão vêm das configurações."""
        client = VLLMClient()

        assert client.base_url == settings.vllm_base_url.rstrip("/")
        assert client.model == settings.vllm_model
        assert client.timeout == settings.vllm_timeout_seconds

