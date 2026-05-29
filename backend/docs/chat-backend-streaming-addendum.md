# Adendo ao backend — Endpoint de streaming de chat

Data: 2026-05-28  
Status: Implementado

Este documento é um adendo à documentação operacional do backend. Ele descreve o endpoint de streaming implementado sem substituir o contrato existente.

## Endpoint não-streaming existente

Permanece inalterado:

```text
POST /chat/conversations/{conversation_id}/generate
```

## Endpoint streaming novo

```text
POST /chat/conversations/{conversation_id}/generate/stream
```

Payload igual ao endpoint não-streaming:

```json
{
  "content": "Mensagem do usuário"
}
```

## Autenticação

Mesma autenticação Bearer do restante da API.

```http
Authorization: Bearer <token>
```

## Resposta

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

## Chunks normais

Texto puro, em mensagens SSE `data:` sem nome de evento:

```text
data: Olá

data: , Eduardo.
```

Não são objetos JSON de token:

```text
data: {"token":"Olá"}
```

Quebras de linha, linhas em branco, indentação e Markdown são preservados por múltiplas linhas `data:` dentro do mesmo evento SSE:

```text
data: ```python
data: print("oi")
data: ```
```

O cliente deve reconstruir essas linhas como texto normal do assistant.

## Eventos de controle

Conclusão:

```text
event: done
data: {"message_id":"..."}
```

Erro:

```text
event: error
data: {"detail":"Falha ao gerar resposta"}
```

Somente `done` e `error` devem ser interpretados como JSON pelo cliente.

## Persistência

Em sucesso:

```text
user message persistida antes da geração
assistant message persistida depois da geração completa
done emitido após persistência do assistant
```

Em erro/desconexão:

```text
user message pode permanecer persistida
assistant parcial não deve ser persistida
done não deve ser emitido
```

## Teste manual

```bash
curl -N \
  -H "Authorization: Bearer $LABIA_CHAT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST \
  "http://127.0.0.1:8010/chat/conversations/$CONVERSATION_ID/generate/stream" \
  -d '{"content":"Responda em Markdown."}'
```

## CLI

O CLI usa streaming por padrão:

```bash
labia-chat chat send "$CONVERSATION_ID" "Responda em uma frase curta."
labia-chat chat
```

Fallback não-streaming:

```bash
labia-chat chat send "$CONVERSATION_ID" "Responda em uma frase curta." --no-stream
labia-chat chat --no-stream
```

## Observações para operação

Se houver proxy reverso, garantir que buffering esteja desabilitado para este endpoint.

Para nginx, avaliar configuração compatível com SSE, além do header:

```text
X-Accel-Buffering: no
```

## Segurança

Nunca emitir no stream:

```text
AI-Scope token
VLLM_API_KEY
DATABASE_URL
stack trace
```
