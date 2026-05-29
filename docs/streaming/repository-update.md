# Atualização do repositório — documentação de streaming

Data: 2026-05-28

## 1. Estado da branch

```bash
cd ~/dev/labia-chat

git status --short
```

Branch esperada: `feature/chat-streaming`.

## 2. Validação final

```bash
cd backend
python -m ruff check src/ tests/
python -m pytest tests/ -q
python -m alembic current
cd ..

git diff --check
git diff --stat
git status --short
```

Smoke:

```bash
bash backend/scripts/smoke_cli.sh
bash backend/scripts/smoke_cli.sh --with-model
```

Checagem manual streaming:

```bash
labia-chat chat send "$CONVERSATION_ID" "Responda em duas linhas."
labia-chat chat send "$CONVERSATION_ID" "Responda em uma frase curta." --no-stream
```

## 3. Contrato final

Streaming:

```text
POST /chat/conversations/{conversation_id}/generate/stream
Content-Type: text/event-stream
```

Chunks normais:

```text
data: pedaço da resposta
```

Não usar:

```text
data: {"token":"..."}
```

Controle:

```text
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}
```

`POST /chat/conversations/{conversation_id}/generate` continua disponível como fallback não-streaming.

## 4. O que não deve mudar

Não mudar:

```text
GET /health
GET /auth/me
GET /chat/conversations
POST /chat/conversations
GET /chat/conversations/{conversation_id}
POST /chat/conversations/{conversation_id}/archive
GET /chat/conversations/{conversation_id}/messages
POST /chat/conversations/{conversation_id}/messages
POST /chat/conversations/{conversation_id}/generate
POST /chat/model/ping
```

Não mudar:

```text
paginação
ownership
schemas existentes
modelos
migrations
frontend
token handling
```

## 5. Comunicação com frontend

Resumo para Gustavo:

```text
Foi adicionado POST /chat/conversations/{conversation_id}/generate/stream.

Ele retorna text/event-stream.

Chunks normais são texto puro:
data: pedaço da resposta

Não será:
data: {"token":"..."}

Eventos de controle:
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}

O endpoint antigo /generate continua igual.

Use fetch(), não EventSource, porque é POST com Authorization e body JSON.
Leia response.body com getReader().
Anexe chunks normais diretamente no conteúdo do assistant.
Faça JSON.parse apenas nos eventos done/error.
Use AbortController ao sair da conversa ou cancelar a geração.
```

## 6. Checklist final de PR

- [ ] `python -m ruff check src/ tests/`
- [ ] `python -m pytest tests/ -q`
- [ ] `python -m alembic current`
- [ ] `bash backend/scripts/smoke_cli.sh`
- [ ] `bash backend/scripts/smoke_cli.sh --with-model`
- [ ] Checagem manual de streaming via CLI ou `curl -N`
