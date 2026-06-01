# labia-chat

Backend FastAPI para chat com modelos locais servidos via vLLM, integrado à autenticação do AI-Scope/ADSS.

## Estado do projeto

O backend mínimo de chat persistente já está implementado.

O projeto possui atualmente:

- autenticação via token AI-Scope/ADSS;
- sincronização de usuário autenticado no banco local;
- persistência de conversas e mensagens;
- endpoints REST para conversas e mensagens;
- integração com vLLM OpenAI-compatible;
- endpoint diagnóstico de geração;
- endpoint de geração persistente;
- endpoint SSE de geração persistente em streaming;
- CLI de chat com streaming por padrão;
- documentação operacional do backend.

A decisão atual é manter o contrato backend documentado antes de iniciar o frontend.

## Estrutura principal

- `backend/` — backend FastAPI.
- `backend/docs/chat-backend.md` — documentação operacional do backend.
- `docs/plans/` — planos históricos de implementação.
- `docs/roadmap-backend-to-frontend.md` — roadmap atualizado do backend até o frontend.
- `docs/cli-chat.md` — especificação inicial do CLI.
- `docs/backend-completion-checklist.md` — checklist para fechamento do backend.
- `docs/frontend-handoff.md` — critérios para iniciar o frontend depois do backend freeze.
- `docs/streaming/` — contrato final de streaming SSE e handoff para frontend.
- `legacy/nextjs-prototype/` — protótipo Next.js legado preservado.

## Documentação

### Backend

Veja:

- [backend/docs/chat-backend.md](backend/docs/chat-backend.md)

Esse documento cobre:

- fluxo AI-Scope → backend → vLLM → persistência;
- variáveis de ambiente;
- avisos de segurança;
- como rodar o backend;
- como testar endpoints via curl;
- troubleshooting;
- paginação de conversas e mensagens (MVP 2.15).

### Roadmap atual

Veja:

- [docs/roadmap-backend-to-frontend.md](docs/roadmap-backend-to-frontend.md)

### CLI

Veja:

- [docs/cli-chat.md](docs/cli-chat.md)
- [docs/cli/README.md](docs/cli/README.md)

O CLI usa streaming por padrão em `labia-chat chat` e
`labia-chat chat send <conversation-id> "mensagem"`.
Use `--no-stream` nesses comandos para forçar o endpoint não-streaming `/generate`.

Quickstart:

```bash
cd backend
python -m pip install -e ".[dev]"
export LABIA_CHAT_API_URL=http://127.0.0.1:8010
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo

labia-chat config init [--api-url <url>] [--streaming-default <true|false>] [--show-last-default <n>]
labia-chat config show
labia-chat doctor
labia-chat conversations list
labia-chat
```

Use `labia-chat chat send <conversation-id> "Olá" --no-stream` ou
`labia-chat chat --no-stream` quando precisar chamar o endpoint não-streaming.

### Resume da conversa mais recente

Para retomar sua conversa mais recente:

```bash
labia-chat --last
labia-chat --resume-last
labia-chat chat --last
labia-chat chat --resume-last
```

Se não houver conversas anteriores, uma nova conversa será criada automaticamente.

Para retomar uma conversa específica pelo ID:

```bash
labia-chat --conversation-id <id> --show-last 5
```

### Streaming SSE

Veja:

- [docs/streaming/README.md](docs/streaming/README.md)
- [docs/streaming/api-contract.md](docs/streaming/api-contract.md)
- [docs/streaming/frontend-integration.md](docs/streaming/frontend-integration.md)

Contrato principal:

- `POST /chat/conversations/{conversation_id}/generate/stream` retorna `text/event-stream`.
- Chunks normais são mensagens SSE `data:` com texto puro, não objetos JSON `{"token": "..."}`.
- `POST /chat/conversations/{conversation_id}/generate` continua disponível como endpoint não-streaming.

### Handoff para frontend

Veja:

- [docs/frontend-handoff.md](docs/frontend-handoff.md)

## Validação padrão do backend

    cd backend
    python -m pytest tests/ -v
    python -m ruff check src/ tests/
    python -m alembic current

Smoke operacional:

    bash backend/scripts/smoke_cli.sh
    bash backend/scripts/smoke_cli.sh --with-model

## Portas locais adotadas

- `8000` — vLLM local OpenAI-compatible.
- `8010` — backend FastAPI `labia-chat`.
- `3000` — futuro frontend dev.

## Segurança

Nunca commite:

- token AI-Scope real;
- `VLLM_API_KEY` real;
- `DATABASE_URL` real com senha;
- arquivos `.env` locais.
