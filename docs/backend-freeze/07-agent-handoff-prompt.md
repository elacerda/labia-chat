# 07 — Prompt de Handoff para Agente/Modelo de Implementação

Use este prompt quando outro programador quiser pedir a um agente de IA para trabalhar no repositório.

Observação: prompts para agentes de implementação devem ser em inglês.

```text
You are working in the `labia-chat` repository.

The backend is in an operational freeze state after MVP 2.16. Do not modify backend behavior unless explicitly asked.

Current frozen scope:
- FastAPI backend under `backend/`
- AI-Scope/ADSS authentication
- required role: `chat_vllm`
- PostgreSQL persistence via SQLAlchemy async and Alembic
- conversations and messages persistence
- vLLM OpenAI-compatible integration
- CLI entry point: `labia-chat`
- CLI smoke script: `backend/scripts/smoke_cli.sh`
- pagination and limits:
  - GET /chat/conversations?limit=20&offset=0, max limit 100
  - GET /chat/conversations/{conversation_id}/messages?limit=50&offset=0, max limit 200
- response shapes remain plain lists for list endpoints; do not add wrappers or pagination metadata unless explicitly requested.

Before making changes:
1. Read `docs/backend-freeze/README.md`.
2. Read `docs/backend-freeze/00-backend-freeze-status.md`.
3. Read `docs/backend-freeze/01-api-contract.md`.
4. Read `docs/backend-freeze/06-change-policy-after-freeze.md`.

Hard constraints:
- Do not save or print tokens.
- Do not add frontend code unless explicitly instructed.
- Do not add dependencies unless explicitly instructed.
- Do not change API response shapes unless explicitly instructed.
- Do not implement streaming, WebSocket, RAG, uploads, tools/function calling, or automatic ADSS login unless explicitly instructed.
- Keep patches small and focused.
- Do not print full diffs.

Validation to run after changes:
cd backend
python -m ruff check src/ tests/
python -m pytest tests/ -q
python -m alembic current
cd ..

git diff --check
git diff --stat
git status --short

For operational validation when a token is available:
bash backend/scripts/smoke_cli.sh
bash backend/scripts/smoke_cli.sh --with-model
```
