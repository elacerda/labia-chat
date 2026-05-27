# 05 — Endpoints planejados

## Convenções

Rotas protegidas recebem:

```http
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

No MVP, esse token é validado diretamente contra o AI-Scope.

## Health

### `GET /health`

Verifica se o backend está vivo.

Resposta:

```json
{
  "status": "ok"
}
```

### `GET /health/adss`

Verifica se o backend consegue alcançar o AI-Scope/ADSS.

Pode ser público ou protegido, a decidir.

### `GET /health/vllm`

Verifica se o backend consegue alcançar o servidor vLLM.

Resposta conceitual:

```json
{
  "status": "online",
  "latency_ms": 42
}
```

## Autenticação

### `GET /auth/me`

Valida token AI-Scope e retorna usuário normalizado.

Request:

```http
GET /auth/me
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

Resposta:

```json
{
  "id": "beae96f3-a2b0-42c6-8b9d-fdc112177638",
  "username": "teste",
  "email": "teste@teste.com",
  "full_name": "teste",
  "roles": ["public", "chat_vllm"]
}
```

## Modelos

### `GET /models`

Lista modelos disponíveis.

Pode ser protegido.

Resposta:

```json
{
  "models": [
    {
      "id": "qwen-coder-next",
      "display_name": "Qwen3-Coder-Next FP8",
      "provider": "openai_compatible",
      "context_window": 65536,
      "supports_streaming": true,
      "supports_tools": false,
      "supports_vision": false
    }
  ]
}
```

## Conversas

### `POST /conversations`

Cria conversa.

Request:

```json
{
  "model_id": "qwen-coder-next",
  "title": "Nova conversa",
  "system_prompt": "opcional"
}
```

### `GET /conversations`

Lista conversas do usuário autenticado.

### `GET /conversations/{conversation_id}`

Obtém conversa com mensagens.

Deve garantir que a conversa pertence ao usuário autenticado.

### `PATCH /conversations/{conversation_id}`

Atualiza título ou arquivamento.

### `DELETE /conversations/{conversation_id}`

Remove/arquiva conversa.

Recomendação MVP: soft delete com `archived_at`.

## Chat

### `POST /chat/stream`

Endpoint principal de envio de mensagem com streaming SSE.

Request:

```json
{
  "conversation_id": "opcional",
  "model_id": "qwen-coder-next",
  "message": "Explique o que é um transformer.",
  "system_prompt": "opcional",
  "temperature": 0.2,
  "max_tokens": 2048
}
```

Comportamento:

1. Valida token AI-Scope.
2. Exige role `chat_vllm`.
3. Sincroniza usuário local.
4. Cria conversa se `conversation_id` não for informado.
5. Salva mensagem do usuário.
6. Monta histórico para o modelo.
7. Chama vLLM.
8. Retorna streaming SSE.
9. Salva resposta final do assistant.

Eventos SSE conceituais:

```text
event: message_start
data: {"conversation_id":"...", "message_id":"..."}

event: message_delta
data: {"content":"Transformers"}

event: message_delta
data: {"content":" são arquiteturas..."}

event: message_done
data: {"conversation_id":"...", "message_id":"..."}

event: error
data: {"message":"..."}
```

## Endpoints futuros

### `POST /auth/callback`

Fase futura para trocar token AI-Scope por sessão própria do `labia-chat`.

### `POST /messages/{message_id}/feedback`

Fase futura para avaliação de respostas.

### Tool calling

Fase futura, implementada no backend e não no frontend.
