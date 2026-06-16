# 03 — Ambiente e Runbook

## Portas adotadas

| Porta | Serviço |
|---:|---|
| `8000` | vLLM local OpenAI-compatible |
| `8010` | backend FastAPI `labia-chat` |
| `3000` | futuro frontend dev, ainda fora do escopo |

## Variáveis de ambiente do backend

Exemplo de desenvolvimento:

```env
DATABASE_URL=postgresql+asyncpg://cbpfuser:SENHA_URL_ENCODED@127.0.0.1:4320/labia_chat

ADSS_BASE_URL=https://ai-scope.cbpf.br/adss/v1
ADSS_REQUIRED_ROLE=chat_vllm
ADSS_AUTH_CACHE_TTL_SECONDS=300
ADSS_TIMEOUT_SECONDS=10

VLLM_BASE_URL=http://127.0.0.1:8000
VLLM_MODEL=qwen-coder-next
VLLM_TIMEOUT_SECONDS=30
# VLLM_API_KEY=your-vllm-api-key-here

VLLM_TEMPERATURE=0.0
VLLM_MAX_TOKENS=512
```

## Variáveis de ambiente do CLI

```env
LABIA_CHAT_API_URL=http://127.0.0.1:8010
LABIA_CHAT_TOKEN=<AI_SCOPE_ACCESS_TOKEN>
```

## Subir backend local

Na raiz do repositório:

```bash
cd backend

python -m uvicorn labia_chat.main:app   --host 127.0.0.1   --port 8010   --reload
```

Validar:

```bash
curl http://127.0.0.1:8010/health
```

Resposta esperada:

```json
{"status":"ok","service":"labia-chat"}
```

## Validar suite padrão

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

## Validar CLI com token

Forma mais segura para sessão interativa:

```bash
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo
```

Depois:

```bash
labia-chat auth me
```

## Smoke core

```bash
bash backend/scripts/smoke_cli.sh
```

## Smoke completo com modelo

Requer backend e vLLM rodando:

```bash
bash backend/scripts/smoke_cli.sh --with-model
```
