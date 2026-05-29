# Testes e validação — Streaming SSE

Data: 2026-05-28

## 1. Validação padrão

Depois de qualquer mudança:

```bash
cd backend
python -m ruff check src/ tests/
python -m pytest tests/ -q
python -m alembic current
cd ..

git diff --check
git diff --stat
git status --short
```

Quando ambiente operacional estiver disponível:

```bash
bash backend/scripts/smoke_cli.sh
bash backend/scripts/smoke_cli.sh --with-model
```

Checklist final de PR:

- [ ] `python -m ruff check src/ tests/`
- [ ] `python -m pytest tests/ -q`
- [ ] `python -m alembic current`
- [ ] `bash backend/scripts/smoke_cli.sh`
- [ ] `bash backend/scripts/smoke_cli.sh --with-model`
- [ ] Checagem manual de streaming via CLI ou `curl -N`

## 2. Testes unitários obrigatórios

### 2.1 Helpers SSE

Cobrir:

- texto simples;
- string vazia;
- chunk `"\n"`;
- chunk `"\n\n"`;
- newline final;
- Markdown code fence;
- indentação;
- caracteres Unicode.

Exemplos:

```python
def test_sse_text_preserves_single_newline_chunk():
    assert sse_text("\n") == "data: \ndata: \n\n"


def test_sse_text_preserves_markdown_code_fence_chunk():
    assert sse_text("```python\n") == "data: ```python\ndata: \n\n"


def test_sse_json_event_encodes_done():
    assert (
        sse_json_event({"message_id": "123"}, event="done")
        == 'event: done\ndata: {"message_id":"123"}\n\n'
    )
```

A saída do JSON usa separadores compactos.

### 2.2 Parsing vLLM streaming

Simular chunks OpenAI-compatible:

```text
data: {"choices":[{"delta":{"content":"Olá"}}]}

data: {"choices":[{"delta":{"content":" mundo"}}]}

data: [DONE]
```

Verificar que o cliente gera:

```python
["Olá", " mundo"]
```

Cobrir:

- chunk vazio;
- delta sem content;
- JSON malformado;
- status HTTP de erro;
- timeout;
- mensagem de erro sem segredo.

### 2.3 Serviço de completion streaming

Cobrir:

- persiste user message antes da geração;
- persiste assistant apenas no sucesso;
- não persiste assistant parcial em erro;
- não mantém transação aberta durante todo o streaming;
- ownership/authorization preservados.

### 2.4 Endpoint FastAPI

Cobrir:

- retorna `text/event-stream`;
- headers anti-buffering presentes;
- stream contém chunks de texto puro;
- stream contém evento `done`;
- erro durante geração emite `event: error`;
- endpoint `/generate` antigo continua funcionando.

## 3. Teste manual com curl

```bash
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo

CONVERSATION_ID="<uuid>"

curl -N \
  -H "Authorization: Bearer $LABIA_CHAT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -X POST \
  "http://127.0.0.1:8010/chat/conversations/$CONVERSATION_ID/generate/stream" \
  -d '{"content":"Responda com uma lista curta em Markdown."}'
```

Esperado:

```text
data: ...

data: ...

event: done
data: {"message_id":"..."}
```

### 3.1 CLI streaming padrão

```bash
labia-chat chat send "$CONVERSATION_ID" "Responda com uma lista curta em Markdown."
```

No chat interativo:

```bash
labia-chat chat
```

### 3.2 CLI fallback não-streaming

```bash
labia-chat chat send "$CONVERSATION_ID" "Responda em uma frase curta." --no-stream
labia-chat chat --no-stream
```

## 4. Smoke operacional

O script existente deve continuar passando. Com `--with-model`, o envio via `labia-chat chat send` usa streaming por padrão.

```bash
bash backend/scripts/smoke_cli.sh
bash backend/scripts/smoke_cli.sh --with-model
```

## 5. Critérios de regressão

Falhar a tarefa se:

- `/generate` mudar comportamento;
- respostas de listagem forem embrulhadas em wrapper novo;
- paginação mudar;
- token aparecer em logs/testes;
- `{"token": ...}` aparecer em chunks normais;
- `\n` e Markdown forem corrompidos;
- assistant parcial for persistido em erro;
- transação de banco ficar aberta durante streaming.
