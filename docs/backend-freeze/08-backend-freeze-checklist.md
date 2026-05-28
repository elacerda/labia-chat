# 08 — Checklist de Backend Freeze

Use este checklist para confirmar que o backend continua congelado e operacional.

## Código e testes

- [ ] `python -m ruff check src/ tests/` passa.
- [ ] `python -m pytest tests/ -q` passa.
- [ ] `python -m alembic current` aponta para `508ff376ee00 (head)` ou head atual documentado.
- [ ] `git diff --check` não reporta problemas.
- [ ] `git status --short` contém apenas mudanças esperadas.

## API

- [ ] `GET /health` retorna `status=ok`.
- [ ] `GET /auth/me` valida token e usuário.
- [ ] `GET /chat/conversations?limit=20&offset=0` funciona.
- [ ] `GET /chat/conversations/{id}/messages?limit=50&offset=0` funciona.
- [ ] valores inválidos de `limit/offset` retornam 422.
- [ ] ownership de conversas/mensagens é preservado.
- [ ] mensagens continuam em ordem cronológica.
- [ ] conversas continuam na ordem esperada, mais recentes primeiro.

## CLI

- [ ] `labia-chat auth me` funciona.
- [ ] `labia-chat conversations create --title "Teste"` funciona.
- [ ] `labia-chat conversations list --limit 5 --offset 0` funciona.
- [ ] `labia-chat messages list <id> --limit 10 --offset 0` funciona.
- [ ] conversa vazia exibe mensagem amigável e retorna exit code `0`.
- [ ] `labia-chat chat send <id> "mensagem"` funciona quando vLLM está disponível.
- [ ] CLI não imprime token.

## Smoke

- [ ] `bash backend/scripts/smoke_cli.sh` passa.
- [ ] `bash backend/scripts/smoke_cli.sh --with-model` passa quando vLLM está disponível.
- [ ] smoke não imprime token.
- [ ] smoke aceita conversa recém-criada sem mensagens.
- [ ] smoke com modelo não depende de texto determinístico gerado pelo LLM.

## Segurança

- [ ] nenhum segredo foi commitado.
- [ ] `.env` real não foi commitado.
- [ ] logs não contêm bearer token.
- [ ] documentação usa placeholders.
