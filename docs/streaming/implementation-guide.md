# Guia de implementação — Streaming SSE no backend

Data: 2026-05-28  
Escopo: implementação backend sem alterar o endpoint não-streaming

## 1. Branch recomendada

```bash
cd ~/dev/labia-chat

git checkout main
git pull --ff-only origin main
git switch -c feature/chat-streaming
git push -u origin feature/chat-streaming
```

Não implementar isso em `cli/eduardo-next`, porque streaming adiciona contrato backend novo.

## 2. Arquivos prováveis

A lista exata deve ser confirmada por inspeção do repositório, mas os arquivos prováveis são:

```text
backend/src/labia_chat/services/vllm_client.py
backend/src/labia_chat/services/chat_generation.py
backend/src/labia_chat/services/chat_completion.py
backend/src/labia_chat/api/routes/chat.py
backend/src/labia_chat/api/deps.py
backend/tests/test_vllm_client.py
backend/tests/test_chat_generation.py
backend/tests/test_chat_completion.py
backend/tests/test_chat_routes.py
```

Possível novo arquivo:

```text
backend/src/labia_chat/api/sse.py
```

ou:

```text
backend/src/labia_chat/services/streaming.py
```

Preferir helper pequeno, isolado e bem testado.

## 3. Helper SSE

Criar helpers sem dependências pesadas.

Exemplo:

```python
import json
from typing import Any


def sse_text(text: str) -> str:
    """Encode plain text as an SSE data message."""
    if text == "":
        return ""

    safe_text = text.replace("\n", "\ndata: ")
    return f"data: {safe_text}\n\n"


def sse_json_event(event: str, payload: dict[str, Any]) -> str:
    """Encode a named SSE event with a JSON payload."""
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"
```

Testar:

```python
def test_sse_text_preserves_plain_text():
    assert sse_text("hello") == "data: hello\n\n"


def test_sse_text_preserves_single_newline_chunk():
    assert sse_text("\n") == "data: \ndata: \n\n"


def test_sse_text_preserves_trailing_newline():
    assert sse_text("hello\n") == "data: hello\ndata: \n\n"


def test_sse_text_preserves_multiple_newlines():
    assert sse_text("\n\n") == "data: \ndata: \ndata: \n\n"


def test_sse_text_preserves_markdown_code_fence_chunk():
    assert sse_text("```python\n") == "data: ```python\ndata: \n\n"


def test_sse_text_skips_empty_string():
    assert sse_text("") == ""
```

## 4. vLLM streaming

O `VLLMClient` deve ganhar método de streaming, por exemplo:

```python
async def stream_chat_completion(
    self,
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
) -> AsyncIterator[str]:
    ...
```

Regras:

- chamar endpoint OpenAI-compatible com `stream=true`;
- extrair deltas de texto;
- ignorar chunks vazios;
- finalizar ao receber `[DONE]`, se o protocolo upstream usar esse marcador;
- não expor payloads com segredos em exceções;
- tratar timeouts e falhas de rede com erro do domínio já usado no projeto.

Pseudocódigo conceitual:

```python
payload = {
    "model": self.model,
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens,
    "stream": True,
}

async with self._client.stream("POST", "/chat/completions", json=payload) as response:
    response.raise_for_status()
    async for line in response.aiter_lines():
        if not line:
            continue
        if not line.startswith("data: "):
            continue

        raw = line.removeprefix("data: ").strip()
        if raw == "[DONE]":
            break

        chunk = json.loads(raw)
        delta = chunk["choices"][0].get("delta", {}).get("content")
        if delta:
            yield delta
```

Adaptar ao cliente HTTP real usado pelo repositório.

## 5. ChatGenerationService

Adicionar método streaming no serviço de geração, por exemplo:

```python
async def stream_response(
    self,
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    async for delta in self.vllm_client.stream_chat_completion(
        messages,
        temperature=self.temperature,
        max_tokens=self.max_tokens,
    ):
        yield delta
```

Manter o método não-streaming atual intacto.

## 6. ChatCompletionService

Este é o ponto mais delicado.

Objetivo:

- persistir user message antes;
- buscar histórico;
- iniciar streaming;
- acumular assistant text;
- emitir deltas para endpoint;
- persistir assistant message apenas após conclusão completa.

Não manter uma sessão/transação aberta durante todo o streaming.

### Modelo conceitual

```python
async def stream_generate_for_conversation(...):
    user_message = await persistence.create_user_message(...)
    history = await persistence.list_messages_for_generation(...)

    assistant_parts: list[str] = []

    async for delta in generation_service.stream_response(history):
        assistant_parts.append(delta)
        yield delta

    assistant_content = "".join(assistant_parts)
    assistant_message = await persistence.create_assistant_message(
        conversation_id=conversation_id,
        content=assistant_content,
    )

    return assistant_message
```

Como `async generator` não retorna valor final de forma conveniente para o endpoint, pode ser melhor o endpoint/serviço produzir eventos internos:

```python
@dataclass(frozen=True)
class ChatStreamDelta:
    text: str


@dataclass(frozen=True)
class ChatStreamDone:
    message_id: UUID
```

ou o endpoint acumular e persistir ao final chamando métodos separados.

Escolher a opção mais simples e testável conforme o código atual.

## 7. Endpoint FastAPI

Adicionar endpoint novo em `chat.py`, mantendo dependências existentes.

Modelo conceitual:

```python
from fastapi.responses import StreamingResponse


@router.post("/chat/conversations/{conversation_id}/generate/stream")
async def generate_message_stream(...):
    async def event_stream():
        try:
            async for event in chat_completion_service.stream_generate(...):
                if isinstance(event, ChatStreamDelta):
                    yield sse_text(event.text)
                elif isinstance(event, ChatStreamDone):
                    yield sse_json_event("done", {"message_id": str(event.message_id)})
        except Exception:
            yield sse_json_event("error", {"detail": "Falha ao gerar resposta"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

O exemplo acima é conceitual. Integrar ao padrão de erros do projeto.

## 8. Desconexão do cliente

Verificar como o endpoint atual acessa `Request`. Para detectar desconexão:

```python
from fastapi import Request

if await request.is_disconnected():
    break
```

No caso de desconexão:

- interromper o loop;
- tentar cancelar upstream;
- não persistir assistant parcial;
- não emitir `done`.

## 9. Lock/concurrency

O app de referência usa `asyncio.Lock` porque o modelo roda dentro do processo FastAPI/GPU. No `labia-chat`, o modelo roda em vLLM externo. Portanto:

- não copiar o lock automaticamente;
- deixar o vLLM gerenciar concorrência e batching;
- só adicionar limite/semáforo se houver necessidade operacional explícita.

## 10. Erros e segurança

Eventos SSE não devem conter:

```text
AI-Scope token
VLLM_API_KEY
DATABASE_URL
stack trace
payload completo do usuário se contiver dados sensíveis
```

Preferir:

```json
{"detail":"Falha ao gerar resposta"}
```

e logs internos higienizados.

## 11. Preservação do endpoint antigo

Adicionar teste explícito garantindo que:

```text
POST /chat/conversations/{conversation_id}/generate
```

continua passando.

O novo endpoint deve ser aditivo.
