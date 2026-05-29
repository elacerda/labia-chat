# Atualização do repositório — documentação de streaming

Data: 2026-05-28

## 1. Estado recomendado antes de aplicar

```bash
cd ~/dev/labia-chat

git checkout main
git pull --ff-only origin main
git status --short
```

Se o hotfix de lifespan já estiver no `main`, criar branch:

```bash
git switch -c feature/chat-streaming
git push -u origin feature/chat-streaming
```

## 2. Aplicar esta documentação

Na raiz do repositório:

```bash
unzip labia_chat_streaming_docs_package_2026-05-28.zip -d .
```

Verificar:

```bash
git status --short
git diff --check
git diff --stat
```

Esperado: apenas arquivos de documentação.

## 3. Commit da documentação

```bash
git add \
  docs/streaming \
  docs/adr/0002-add-sse-chat-streaming-endpoint.md \
  backend/docs/chat-backend-streaming-addendum.md

git commit -m "docs: plan SSE chat streaming implementation"
git push
```

## 4. Implementação posterior

Depois do commit de docs, implementar em passos pequenos.

Sugestão de commits:

```text
feat: add SSE encoding helpers
feat: add vLLM streaming client support
feat: add streaming chat completion service
feat: add chat generate streaming endpoint
test: cover SSE chat streaming behavior
docs: document streaming endpoint usage
```

## 5. Validação após implementação

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

Smoke futuro opcional:

```bash
bash backend/scripts/smoke_streaming.sh
```

## 6. O que não deve mudar

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

## 7. Comunicação com frontend

Resumo para Gustavo:

```text
Vamos adicionar POST /chat/conversations/{conversation_id}/generate/stream.

Ele retorna text/event-stream.

Chunks normais serão texto puro:
data: pedaço da resposta

Não será:
data: {"token":"..."}

Eventos de controle:
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}

O endpoint antigo /generate continua igual.
```
