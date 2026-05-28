# 01 — Contrato REST do Backend

## Base URL local

```text
http://127.0.0.1:8010
```

## Autenticação

Os endpoints de chat exigem token AI-Scope/ADSS válido.

O token deve ser enviado pelo cliente como bearer token conforme implementação atual do CLI/backend.

## Health

```http
GET /health
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "labia-chat"
}
```

## Auth

```http
GET /auth/me
```

Objetivo:

- validar token;
- validar usuário ativo;
- validar role requerida;
- sincronizar usuário em `chat_users`.

Role requerida:

```text
chat_vllm
```

## Chat — conversas

### Listar conversas

```http
GET /chat/conversations?limit=20&offset=0
```

Contrato:

| Parâmetro | Default | Mínimo | Máximo | Descrição |
|---|---:|---:|---:|---|
| `limit` | `20` | `1` | `100` | Quantidade máxima de conversas retornadas |
| `offset` | `0` | `0` | — | Quantidade de conversas a pular |

Regras:

- valores inválidos retornam HTTP 422;
- conversas pertencem ao usuário autenticado;
- ownership deve ser preservado;
- ordenação esperada: conversas mais recentes primeiro, conforme implementação atual;
- resposta permanece lista simples, sem wrapper e sem metadata de paginação nesta MVP.

### Criar conversa

```http
POST /chat/conversations
```

Usado pelo CLI:

```bash
labia-chat conversations create --title "Título"
```

### Obter conversa

```http
GET /chat/conversations/{conversation_id}
```

Regras:

- conversa deve pertencer ao usuário autenticado;
- conversa inexistente ou de outro usuário não deve vazar dados.

### Arquivar conversa

```http
POST /chat/conversations/{conversation_id}/archive
```

## Chat — mensagens

### Listar mensagens

```http
GET /chat/conversations/{conversation_id}/messages?limit=50&offset=0
```

Contrato:

| Parâmetro | Default | Mínimo | Máximo | Descrição |
|---|---:|---:|---:|---|
| `limit` | `50` | `1` | `200` | Quantidade máxima de mensagens retornadas |
| `offset` | `0` | `0` | — | Quantidade de mensagens a pular |

Regras:

- valores inválidos retornam HTTP 422;
- mensagens pertencem a conversa do usuário autenticado;
- ownership deve ser preservado;
- ordenação esperada: cronológica;
- resposta permanece lista simples, sem wrapper e sem metadata de paginação nesta MVP;
- conversa recém-criada pode retornar lista vazia.

### Criar mensagem

```http
POST /chat/conversations/{conversation_id}/messages
```

### Gerar resposta persistente

```http
POST /chat/conversations/{conversation_id}/generate
```

Regras:

- usa histórico persistido da conversa;
- chama vLLM OpenAI-compatible;
- persiste mensagem do usuário e resposta do assistente conforme implementação atual.

## Diagnóstico de modelo

```http
POST /chat/model/ping
```

Objetivo:

- validar integração backend ↔ vLLM;
- depende do vLLM estar acessível em `VLLM_BASE_URL`.

## Erros esperados no CLI

| Caso | Mensagem amigável esperada |
|---|---|
| 401 | `Token inválido ou expirado. Gere um novo token AI-Scope.` |
| 403 | `Usuário autenticado, mas sem permissão chat_vllm.` |
| 404 | `Conversa não encontrada para este usuário.` |
| 422 | `Dados inválidos. Verifique a entrada e tente novamente.` |
| 502 | `Backend não conseguiu obter resposta do modelo.` |
| timeout | `Timeout ao conectar ao backend. Tente novamente.` |
| rede | `Falha de conexão com o backend. Verifique sua rede.` |
| payload inesperado | `Resposta inesperada do backend. Tente novamente.` |
