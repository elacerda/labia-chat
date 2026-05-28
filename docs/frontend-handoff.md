# Handoff para desenvolvimento do frontend

Data de referência: 2026-05-28  
Projeto: `labia-chat`

Este documento define o que o backend deve entregar para que outra pessoa desenvolvedora possa iniciar o frontend com segurança.

## 1. Pré-condição

O frontend só deve ser retomado depois do backend freeze.

Backend freeze significa:

- API mínima de chat estável;
- CLI usado como cliente real;
- erros documentados;
- autenticação documentada;
- endpoints e schemas públicos documentados;
- smoke test reproduzível.

## 2. URLs locais esperadas

```text
vLLM local:       http://127.0.0.1:8000
backend FastAPI: http://127.0.0.1:8010
frontend futuro: http://127.0.0.1:3000
```

## 3. Autenticação

O frontend MVP deve começar com token manual.

Header obrigatório:

```http
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

Endpoint de validação:

```http
GET /auth/me
```

O frontend não deve receber senha AI-Scope no MVP inicial.

## 4. Fluxo mínimo do frontend

```text
1. Usuário cola token AI-Scope.
2. Frontend chama GET /auth/me.
3. Frontend lista conversas.
4. Usuário cria ou seleciona conversa.
5. Frontend lista mensagens.
6. Usuário envia mensagem.
7. Frontend chama POST /chat/conversations/{id}/generate.
8. Frontend exibe resposta assistant persistida.
```

## 5. Endpoints mínimos

```http
GET    /auth/me
GET    /chat/conversations
POST   /chat/conversations
GET    /chat/conversations/{conversation_id}
GET    /chat/conversations/{conversation_id}/messages
POST   /chat/conversations/{conversation_id}/generate
POST   /chat/conversations/{conversation_id}/archive
```

## 6. Contrato esperado

### Conversa

Campos públicos esperados:

```json
{
  "id": "uuid",
  "title": "string or null",
  "metadata": {},
  "created_at": "datetime",
  "updated_at": "datetime",
  "archived_at": "datetime or null"
}
```

O frontend não deve depender de `user_id`.

### Mensagem

Campos públicos esperados:

```json
{
  "id": "uuid",
  "conversation_id": "uuid",
  "role": "user | assistant | system | tool",
  "content": "string",
  "sequence_index": 0,
  "model": "string or null",
  "metadata": {},
  "created_at": "datetime"
}
```

## 7. Erros que o frontend deve tratar

| Status | Tratamento de UX |
|--------|-------------------|
| 401 | pedir novo token |
| 403 | mostrar ausência de permissão `chat_vllm` |
| 404 | conversa não encontrada |
| 422 | erro de entrada/UUID inválido |
| 502 | falha temporária do modelo/vLLM |

## 8. Fora de escopo do primeiro frontend

- streaming;
- websocket;
- RAG;
- upload de arquivos;
- login redirect completo;
- múltiplos modelos;
- tools/function calling;
- markdown avançado;
- design final.

## 9. Critério para início do frontend

Antes de criar o frontend:

```bash
cd backend
python -m pytest tests/ -v
python -m ruff check src/ tests/
python -m alembic current
```

E validar pelo CLI:

```bash
labia-chat chat
labia-chat auth me
labia-chat conversations list
```

## 10. Observações para a pessoa desenvolvedora frontend

- O backend é a fonte de verdade.
- Não persistir histórico no navegador como substituto do backend.
- Token pode ser mantido em memória no primeiro MVP.
- Persistir token em `localStorage` deve ser decisão explícita, pois aumenta risco de exposição.
