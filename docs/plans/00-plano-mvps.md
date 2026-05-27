# 00 — Plano de MVPs do novo `labia-chat`

## MVP 0 — Estrutura inicial do backend

Objetivo: criar base FastAPI executável.

Inclui:

- `backend/` com estrutura inicial.
- `pyproject.toml`.
- FastAPI.
- Uvicorn.
- Pydantic Settings.
- `.env.example`.
- `GET /health`.
- pytest básico.
- ruff básico.

Critério de pronto:

- `uvicorn labia_chat.main:app --reload` sobe.
- `GET /health` retorna `{ "status": "ok" }`.
- Testes básicos passam.

## MVP 1 — Autenticação AI-Scope

Objetivo: validar token AI-Scope e exigir role `chat_vllm`.

Inclui:

- Cliente ADSS com httpx.
- Extração de Bearer token.
- `GET /auth/me`.
- Validação de `is_active`.
- Validação da role configurável `ADSS_REQUIRED_ROLE`.
- Cache curto opcional de validação.
- Testes com mock do ADSS.

Critério de pronto:

- Token válido com role acessa `/auth/me`.
- Token inválido retorna 401.
- Usuário sem role retorna 403.

## MVP 2 — Banco e migrações

Objetivo: adicionar PostgreSQL, SQLAlchemy 2 async e Alembic.

Inclui:

- Conexão async com PostgreSQL.
- Configuração `DATABASE_URL`.
- Alembic.
- Modelos `chat_users`, `chat_conversations`, `chat_messages`.
- Migração inicial.

Critério de pronto:

- `alembic upgrade head` cria tabelas.
- Testes conseguem usar banco de teste.

## MVP 3 — Sincronização de usuário

Objetivo: persistir usuário validado localmente.

Inclui:

- Repository de usuários.
- Serviço para upsert de usuário AI-Scope.
- Atualização de `last_seen_at`.
- Roles salvas em JSONB.

Critério de pronto:

- Ao chamar `/auth/me`, usuário é criado/atualizado no banco.

## MVP 4 — Model registry e health vLLM

Objetivo: tornar modelos configuráveis.

Inclui:

- Model registry via `.env`.
- `GET /models`.
- Cliente vLLM básico.
- `GET /health/vllm`.

Critério de pronto:

- `/models` lista o modelo configurado.
- `/health/vllm` indica status do vLLM.

## MVP 5 — Chat streaming stateless

Objetivo: chamar vLLM e transmitir resposta via SSE, sem histórico persistido ainda.

Inclui:

- `POST /chat/stream`.
- Validação AI-Scope.
- Escolha de modelo.
- Chamada streaming ao vLLM.
- Eventos `message_start`, `message_delta`, `message_done`, `error`.

Critério de pronto:

- Requisição com token autorizado retorna stream de resposta do vLLM.

## MVP 6 — Conversas persistidas

Objetivo: salvar histórico em PostgreSQL.

Inclui:

- Criação de conversa automática ou explícita.
- Salvamento da mensagem do usuário.
- Salvamento da resposta do assistant.
- Montagem de histórico por conversa.
- Associação por `user_id` do AI-Scope.

Critério de pronto:

- Mensagens enviadas aparecem na conversa do usuário.
- Usuário não acessa conversa de outro usuário.

## MVP 7 — CRUD de conversas

Objetivo: expor gerenciamento básico de conversas.

Inclui:

- `GET /conversations`.
- `POST /conversations`.
- `GET /conversations/{id}`.
- `PATCH /conversations/{id}`.
- `DELETE /conversations/{id}` com soft delete.

Critério de pronto:

- Cliente consegue criar, listar, abrir, renomear e arquivar conversas.

## MVP futuro — sessão própria do labia-chat

Objetivo: trocar token AI-Scope por sessão própria.

Inclui:

- `POST /auth/callback`.
- Tabela `chat_sessions`.
- Token opaco próprio.
- Armazenamento de hash de token.
- Expiração e revogação.

## MVP futuro — tool calling

Objetivo: implementar tool calling no backend.

Inclui:

- Suporte a tools no model registry.
- Parser robusto de tool calls.
- Execução server-side.
- Eventos SSE de tool calls.
- Persistência de mensagens `tool`.
