# 00 — Estado do Backend Freeze

## Estado consolidado

O backend do `labia-chat` está em estado de congelamento operacional inicial após a MVP 2.16.

O objetivo deste estado é preservar uma base estável para que próximos blocos de desenvolvimento possam ser planejados sem modificar acidentalmente contratos já validados.

## Marcos concluídos

- MVP 2.11 — CLI interativo mínimo.
- MVP 2.12 — retomada de conversa e `/history`.
- MVP 2.13a — comandos não interativos de smoke test.
- MVP 2.13b — comandos de inspeção.
- MVP 2.14 — hardening de erros do CLI/backend.
- MVP 2.15 — paginação e limites para listagem de conversas/mensagens.
- MVP 2.15 docs — documentação do contrato de paginação.
- MVP 2.16 — smoke operacional backend+CLI.
- MVP 2.16 fix — smoke core aceita conversa recém-criada sem mensagens.
- MVP 2.16 fix — smoke `--with-model` valida resposta não vazia, sem depender de texto determinístico do modelo.

## Validações reportadas

Últimas validações reportadas durante o congelamento:

```text
ruff: All checks passed
pytest: 287 passed
alembic current: 508ff376ee00 (head)
smoke core: All checks passed
smoke --with-model: All checks passed
```

Smoke com modelo validou:

- `/health`;
- `labia-chat auth me`;
- criação de conversa;
- listagem de conversas com paginação;
- listagem de mensagens vazia;
- `labia-chat chat send`;
- persistência de mensagens;
- `POST /chat/model/ping`.

## Princípio de congelamento

A partir deste ponto, qualquer mudança no backend deve ser tratada como exceção ou nova MVP explícita.

Antes de modificar código backend, responder:

1. A mudança corrige bug real?
2. Que contrato público ela altera?
3. Quais testes protegem a mudança?
4. O smoke core e o smoke com modelo continuam passando?
5. A documentação afetada foi atualizada?
