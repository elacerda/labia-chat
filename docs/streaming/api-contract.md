# Contrato de API — Chat streaming SSE

Data: 2026-05-28  
Status: contrato proposto para implementação

## 1. Endpoint novo

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

Este endpoint é uma extensão explícita do contrato do backend. Ele não substitui:

```text
POST /chat/conversations/{conversation_id}/generate
```

## 2. Autenticação

Mesma autenticação do endpoint não-streaming:

```http
Authorization: Bearer <AI-Scope token>
```

O token nunca deve ser incluído em logs, mensagens de erro, eventos SSE ou documentação com valor real.

## 3. Request

O payload deve ser o mesmo do endpoint atual de geração persistente.

Exemplo ilustrativo:

```json
{
  "content": "Explique o que é o projeto labia-chat."
}
```

Se o schema real do endpoint atual tiver outro nome de campo, reutilizar exatamente o schema existente. Não criar divergência entre `/generate` e `/generate/stream` sem decisão explícita.

## 4. Response

### Status

Em caso de aceite inicial da requisição:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

Headers recomendados:

```python
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
```

## 5. Protocolo SSE

### 5.1 Chunks normais

Chunks normais devem conter apenas texto da resposta do assistant.

Não usar:

```text
data: {"token": "texto"}
```

Usar:

```text
data: texto
```

Exemplo:

```text
data: Olá

data: , Eduardo.

data: Posso ajudar com o projeto.
```

### 5.2 Evento de conclusão

No final de uma geração bem-sucedida:

```text
event: done
data: {"message_id":"<uuid-da-mensagem-assistant>"}
```

Campos mínimos:

```json
{
  "message_id": "uuid"
}
```

Campos opcionais futuros, se forem úteis:

```json
{
  "message_id": "uuid",
  "conversation_id": "uuid",
  "role": "assistant"
}
```

### 5.3 Evento de erro

Em caso de falha durante a geração:

```text
event: error
data: {"detail":"Falha ao gerar resposta"}
```

Regras:

- Não expor token.
- Não expor `VLLM_API_KEY`.
- Não expor `DATABASE_URL`.
- Não despejar stack trace no evento.
- Log interno pode ter mais contexto, mas sem segredos.

### 5.4 Preservação de quebras de linha

O helper de texto deve preservar chunks como:

```python
"\n"
"\n\n"
"```python\n"
"  indentação"
"\t"
```

Implementação recomendada:

```python
def sse_text(text: str) -> str:
    """Encode plain text as an SSE data message.

    Normal assistant chunks are streamed as plain SSE data messages,
    not JSON objects, to avoid repeating keys such as {"token": "..."}.

    Newlines are encoded as multiple `data:` lines so Markdown,
    code blocks, blank lines, and whitespace-only chunks can be
    reconstructed correctly by an SSE client.
    """
    if text == "":
        return ""

    safe_text = text.replace("\n", "\ndata: ")
    return f"data: {safe_text}\n\n"
```

Para eventos estruturados:

```python
import json
from typing import Any

def sse_json_event(event: str, payload: dict[str, Any]) -> str:
    """Encode a named SSE event with a JSON payload."""
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"
```

## 6. Semântica de persistência

### 6.1 Sucesso

Em uma geração bem-sucedida:

1. persistir mensagem do usuário;
2. gerar resposta via vLLM streaming;
3. acumular resposta completa em memória;
4. persistir mensagem do assistant;
5. emitir `done`.

### 6.2 Falha antes de gerar tokens

- user message pode já ter sido persistida;
- assistant message não deve ser persistida;
- emitir `error`.

### 6.3 Falha após gerar alguns tokens

- user message pode já ter sido persistida;
- assistant parcial não deve ser persistida;
- emitir `error`;
- frontend deve marcar a resposta como falha/parcial localmente, se desejar.

### 6.4 Cliente desconectado

- cancelar upstream quando possível;
- não persistir assistant parcial;
- não manter recursos abertos;
- não manter transação aberta durante o stream.

## 7. Compatibilidade

Endpoint existente preservado:

```text
POST /chat/conversations/{conversation_id}/generate
```

Endpoint novo:

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

Nenhum cliente existente deve quebrar.

## 8. Exemplo com curl

```bash
curl -N \
  -H "Authorization: Bearer $LABIA_CHAT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST \
  "http://127.0.0.1:8010/chat/conversations/$CONVERSATION_ID/generate/stream" \
  -d '{"content":"Olá, responda em duas linhas."}'
```

O `-N` evita buffering do `curl`.

## 9. Exemplo de resposta

```text
data: Olá!

data: Aqui está uma resposta em duas linhas:
data: primeira linha.
data: segunda linha.

event: done
data: {"message_id":"a3c1..."}
```
