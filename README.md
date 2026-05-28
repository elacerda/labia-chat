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
- documentação operacional do backend.

A decisão atual é finalizar completamente o backend antes de iniciar o frontend. O próximo bloco de desenvolvimento é um CLI de chat para validar o backend como cliente real.

## Estrutura principal

- `backend/` — backend FastAPI.
- `backend/docs/chat-backend.md` — documentação operacional do backend.
- `docs/plans/` — planos históricos de implementação.
- `docs/roadmap-backend-to-frontend.md` — roadmap atualizado do backend até o frontend.
- `docs/cli-chat.md` — especificação inicial do CLI.
- `docs/backend-completion-checklist.md` — checklist para fechamento do backend.
- `docs/frontend-handoff.md` — critérios para iniciar o frontend depois do backend freeze.
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

### Handoff para frontend

Veja:

- [docs/frontend-handoff.md](docs/frontend-handoff.md)

## Validação padrão do backend

    cd backend
    python -m pytest tests/ -v
    python -m ruff check src/ tests/
    python -m alembic current

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
