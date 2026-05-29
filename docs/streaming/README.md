# Streaming SSE para respostas de chat no `labia-chat`

Data: 2026-05-28  
Status: Proposta técnica pronta para implementação  
Escopo: backend + contrato frontend + CLI opcional posterior

## 1. Contexto

O backend do `labia-chat` foi congelado operacionalmente após a MVP 2.16. O contrato atual inclui o endpoint de geração persistente não-streaming:

```text
POST /chat/conversations/{conversation_id}/generate
```

O frontend precisa de uma experiência de resposta incremental, semelhante ao ChatGPT e a outros chats de modelos de IA. Isso exige que o backend envie partes da resposta à medida que o modelo as gera, em vez de aguardar a resposta completa.

Esta documentação propõe uma extensão explícita do contrato:

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

O endpoint novo não substitui nem altera o endpoint atual. Ele adiciona uma forma streaming para o frontend e para clientes técnicos.

## 2. Referência conceitual

O app de referência enviado pelo Gustavo implementa streaming com:

- `StreamingResponse`;
- `media_type="text/event-stream"`;
- gerador assíncrono `event_stream()`;
- headers anti-buffering;
- eventos SSE progressivos;
- evento final de conclusão.

No app de referência, os chunks são emitidos como JSON:

```text
data: {"token": "..."}
```

O refinamento solicitado pelo frontend é evitar esse wrapper repetitivo. No `labia-chat`, os chunks normais devem ser emitidos como texto puro:

```text
data: pedaço da resposta
```

Eventos de controle continuam estruturados:

```text
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}
```

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

## 4. Fora de escopo inicial

- WebSocket.
- Cursor pagination.
- Mudanças no endpoint `/generate`.
- Retry automático de geração.
- Persistência de resposta parcial.
- Alteração do sistema de login/token.
- Alteração do frontend dentro desta branch de backend.
- Streaming de metadados a cada chunk.
- Streaming de sources/RAG, pois o `labia-chat` atual não é RAG.

## 5. Divisão sugerida em tarefas

### Tarefa 1 — Planejamento e contrato

Definir contrato SSE, eventos, headers, comportamento de persistência e critérios de aceite.

### Tarefa 2 — Helpers SSE

Criar helpers pequenos e testados para:

- texto puro;
- eventos JSON estruturados;
- preservação de quebras de linha;
- erro/done.

### Tarefa 3 — vLLM streaming

Adicionar suporte a `stream=true` no `VLLMClient`, extraindo deltas de chunks OpenAI-compatible.

### Tarefa 4 — Serviços de geração/completion

Adicionar fluxo de geração streaming preservando as regras de persistência:

- user message antes;
- assistant message apenas após sucesso;
- sem transação aberta durante o streaming.

### Tarefa 5 — Endpoint FastAPI

Adicionar:

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

com `StreamingResponse`.

### Tarefa 6 — Testes

Cobrir helpers, parsing de chunks, endpoint streaming, erro e preservação do endpoint não-streaming.

### Tarefa 7 — CLI opcional

Adicionar consumo streaming no CLI depois que o backend estiver estável.

### Tarefa 8 — Documentação operacional

Atualizar docs para frontend e backend.

## 6. Critérios de aceite

A implementação estará pronta quando:

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
