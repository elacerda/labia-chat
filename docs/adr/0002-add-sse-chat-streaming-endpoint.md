# ADR 0002 — Adicionar endpoint SSE para streaming de respostas de chat

Data: 2026-05-28  
Status: Aceito e implementado

## Contexto

O `labia-chat` possui backend FastAPI com endpoint de geração persistente:

```text
POST /chat/conversations/{conversation_id}/generate
```

Esse endpoint retorna a resposta completa apenas depois que o modelo termina a geração.

O frontend precisa de experiência de chat moderna, em que a resposta aparece incrementalmente conforme o modelo gera tokens/chunks.

O backend foi congelado operacionalmente após a MVP 2.16, então qualquer mudança no contrato REST deve ser explícita e aditiva.

## Decisão

Adicionar um endpoint novo:

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

com resposta:

```http
Content-Type: text/event-stream
```

O endpoint antigo permanece inalterado.

Usar Server-Sent Events com chunks normais em texto puro:

```text
data: texto do assistant
```

e eventos estruturados apenas para controle:

```text
event: done
data: {"message_id":"..."}

event: error
data: {"detail":"..."}
```

## Justificativa

SSE é suficiente para o caso de uso:

- servidor envia tokens/chunks ao cliente;
- cliente não precisa enviar mensagens adicionais durante a mesma conexão;
- funciona bem sobre HTTP;
- integra naturalmente com FastAPI `StreamingResponse`;
- evita a complexidade inicial de WebSockets.

Chunks normais em texto puro reduzem overhead e evitam repetir `{"token": ...}` em cada evento.

Quebras de linha e Markdown são preservados com múltiplas linhas `data:` no mesmo evento SSE. O cliente deve anexar chunks normais como texto e fazer parse JSON apenas dos eventos `done` e `error`.

## Consequências positivas

- Experiência de usuário tipo ChatGPT.
- Contrato antigo preservado.
- Frontend pode renderizar incrementalmente.
- CLI usa o mesmo endpoint por padrão.
- Implementação menor que WebSocket.

## Consequências negativas / riscos

- É necessário lidar com desconexão do cliente.
- Persistência parcial deve ser evitada.
- O frontend precisa de parser SSE para `fetch` streaming.
- Proxies precisam evitar buffering.
- Testes devem cobrir newlines e chunks parciais.

## Mitigações

- Headers anti-buffering:
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`
  - `X-Accel-Buffering: no`
- Não manter transação aberta durante streaming.
- Persistir assistant apenas no sucesso.
- Testes unitários para helpers SSE.
- Testes de regressão para `/generate`.
- Fallback CLI com `--no-stream`.

## Alternativas consideradas

### Alterar `/generate` para streaming

Rejeitado. Quebraria clientes existentes e o contrato congelado.

### WebSocket

Adiado. Mais complexo e desnecessário para streaming unidirecional inicial.

### JSON em cada chunk

Parcialmente rejeitado. O app de referência usa `data: {"token": "..."}`, mas o frontend pediu otimização: enviar somente o texto nos chunks normais.

## Critério de aceite

- `/generate` continua funcionando.
- `/generate/stream` retorna SSE.
- chunks normais são texto puro.
- `done` inclui `message_id`.
- `error` é estruturado.
- newlines e Markdown são preservados.
- assistant parcial não é persistido em erro/desconexão.
- CLI usa streaming por padrão em `chat send` e `chat`.
- CLI mantém fallback `--no-stream` para `/generate`.
