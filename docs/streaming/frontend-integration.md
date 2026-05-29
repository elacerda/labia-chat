# Guia para frontend — consumo do endpoint SSE

Data: 2026-05-28  
Público: frontend do `labia-chat`

Resumo para Gustavo: usar `fetch()` com `ReadableStream`, não `EventSource`, porque o endpoint é `POST`, exige `Authorization` e recebe body JSON.

## 1. Endpoint

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

Headers:

```http
Authorization: Bearer <token>
Content-Type: application/json
Accept: text/event-stream
```

## 2. Formato do stream

Chunks normais são texto puro em eventos SSE `message`:

```text
data: Olá

data: , Eduardo
```

Eles não são JSON:

```text
data: Olá
```

Quebras de linha e Markdown chegam como múltiplas linhas `data:` no mesmo evento SSE e devem ser preservados.

Evento de conclusão:

```text
event: done
data: {"message_id":"..."}
```

Evento de erro:

```text
event: error
data: {"detail":"Falha ao gerar resposta"}
```

## 3. Consumo com fetch

Como a requisição é `POST` com `Authorization`, usar `fetch()` com `ReadableStream`, não `EventSource` simples.

Exemplo conceitual:

```js
async function streamAssistantResponse({
  apiUrl,
  token,
  conversationId,
  payload,
  signal,
}) {
  const response = await fetch(
    `${apiUrl}/chat/conversations/${conversationId}/generate/stream`,
    {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal,
    },
  );

  if (!response.ok || !response.body) {
    throw new Error(`Streaming request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let boundary;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      handleSseEvent(rawEvent);
    }
  }

}
```

## 4. Parser SSE mínimo

```js
function parseSseEvent(rawEvent) {
  const lines = rawEvent.split("\n");
  let eventName = "message";
  const dataLines = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).replace(/^ /, ""));
    }
  }

  return {
    event: eventName,
    data: dataLines.join("\n"),
  };
}
```

## 5. Tratamento de eventos

```js
function handleSseEvent(rawEvent) {
  const event = parseSseEvent(rawEvent);

  if (event.event === "message") {
    // Texto puro. Nao fazer JSON.parse().
    appendToAssistantMessage(event.data);
    return;
  }

  if (event.event === "done") {
    const payload = JSON.parse(event.data);
    finalizeAssistantMessage(payload.message_id);
    return;
  }

  if (event.event === "error") {
    const payload = JSON.parse(event.data);
    markAssistantMessageAsFailed(payload.detail);
    return;
  }
}
```

## 6. Fluxo de UI recomendado

1. Usuário envia mensagem.
2. UI cria mensagem do usuário localmente.
3. UI cria mensagem assistant vazia com estado `streaming`.
4. UI chama endpoint de streaming.
5. A cada evento `message`, concatena `event.data`.
6. Em `done`, marca a mensagem como finalizada e associa `message_id`.
7. Em `error`, marca a mensagem como falha.
8. Se o usuário cancelar, abortar fetch com `AbortController`.

## 7. Cancelamento

```js
const controller = new AbortController();

streamAssistantResponse({
  apiUrl,
  token,
  conversationId,
  payload,
  signal: controller.signal,
});

// Para cancelar:
controller.abort();
```

O backend deve tratar desconexão sem persistir resposta parcial.

Usar cancelamento ao sair da conversa, trocar de conversa ou clicar em parar geração.

## 8. Observações

- O frontend não deve esperar JSON em chunks normais.
- `event.data` dos chunks normais já é texto.
- Eventos `done` e `error` são JSON.
- O frontend deve preservar `\n`, espaços e Markdown.
- Não fazer polling de mensagens durante o stream; aguardar `done` e, se necessário, recarregar mensagens depois.
