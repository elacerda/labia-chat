# Streaming SSE para respostas de chat no `labia-chat`

Data: 2026-05-28
Status: Implementado
Escopo: backend + contrato frontend + CLI

## 1. Contexto

O backend do `labia-chat` foi congelado operacionalmente após a MVP 2.16. O contrato atual inclui o endpoint de geração persistente não-streaming:

```text
POST /chat/conversations/{conversation_id}/generate
```

O frontend precisa de uma experiência de resposta incremental, semelhante ao ChatGPT e a outros chats de modelos de IA. Isso exige que o backend envie partes da resposta à medida que o modelo as gera, em vez de aguardar a resposta completa.

Esta documentação registra a extensão explícita do contrato:

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

O endpoint novo não substitui nem altera o endpoint atual. Ele adiciona uma forma streaming para o frontend e para clientes técnicos.

## 2. Contrato final

O endpoint streaming implementado usa:

- `StreamingResponse`;
- `media_type="text/event-stream"`;
- gerador assíncrono de eventos SSE;
- headers anti-buffering;
- eventos SSE progressivos;
- evento final de conclusão.

Chunks normais são texto puro:

```text
data: pedaço da resposta
```

Não usar JSON repetitivo em chunks normais:

```text
data: {"token": "..."}
```

Eventos de controle continuam estruturados:

```text
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}
```

Quebras de linha e Markdown são preservados com múltiplas linhas `data:` no mesmo evento SSE. O cliente deve juntar essas linhas com `\n` e anexar o resultado diretamente ao conteúdo do assistant.

## 3. Objetivo funcional

Quando o usuário envia uma mensagem:

1. O backend valida autenticação/autorização normalmente.
2. O backend verifica ownership da conversa normalmente.
3. O backend persiste a mensagem do usuário.
4. O backend monta o histórico da conversa.
5. O backend chama o vLLM OpenAI-compatible com `stream=true`.
6. O backend envia chunks de texto via SSE à medida que chegam.
7. O backend acumula a resposta completa em memória.
8. Ao final bem-sucedido, o backend persiste a resposta completa do assistant.
9. O backend envia evento `done`.
10. O frontend finaliza a mensagem em tela.

## 4. CLI

O CLI consome streaming por padrão:

```bash
labia-chat chat send <conversation-id> "Mensagem"
labia-chat chat
```

Fallback para o endpoint não-streaming:

```bash
labia-chat chat send <conversation-id> "Mensagem" --no-stream
labia-chat chat --no-stream
```

## 5. Handoff frontend para Gustavo

- Usar `fetch()`, não `EventSource`, porque a chamada é `POST` com `Authorization` e body JSON.
- Ler `response.body` com `getReader()` e decodificar como UTF-8.
- Para eventos normais `message`, anexar `event.data` diretamente ao texto do assistant.
- Fazer `JSON.parse()` apenas nos eventos `done` e `error`.
- Usar `AbortController` ao sair da conversa ou cancelar a geração.

Exemplo completo e parser mínimo: [frontend-integration.md](frontend-integration.md).

## 6. Fora de escopo inicial

- WebSocket.
- Cursor pagination.
- Mudanças no endpoint `/generate`.
- Retry automático de geração.
- Persistência de resposta parcial.
- Alteração do sistema de login/token.
- Alteração do frontend dentro desta branch de backend.
- Streaming de metadados a cada chunk.
- Streaming de sources/RAG, pois o `labia-chat` atual não é RAG.

## 7. Critérios de aceite

A implementação está pronta quando:

- `/generate` continuar funcionando como antes.
- `/generate/stream` emitir `text/event-stream`.
- chunks normais forem texto puro, sem `{"token": ...}`.
- chunks com `\n`, `\n\n`, espaços e Markdown forem preservados.
- `done` trouxer pelo menos `message_id`.
- `error` for estruturado.
- user message for persistida antes da geração.
- assistant message for persistida apenas após sucesso.
- desconexão/erro não persistir resposta parcial.
- testes passarem.
- smoke existente continuar passando.

## 8. Checklist final de PR

- [ ] `python -m ruff check src/ tests/`
- [ ] `python -m pytest tests/ -q`
- [ ] `python -m alembic current`
- [ ] `bash backend/scripts/smoke_cli.sh`
- [ ] `bash backend/scripts/smoke_cli.sh --with-model`
- [ ] Checagem manual de streaming via CLI ou `curl -N`
