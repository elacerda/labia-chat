# labia-chat Backend

Backend FastAPI para chat com modelos locais.

## Estrutura do Projeto

```
backend/
├── src/
│   └── labia_chat/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       └── health.py
│       └── core/
│           ├── __init__.py
│           └── config.py
├── tests/
│   └── test_health.py
├── pyproject.toml
├── .env.example
└── README.md
```

## Instalação

```bash
cd backend
python -m pip install -e ".[dev]"
```

## Configuração

Copie o arquivo `.env.example` para `.env` e ajuste as variáveis conforme necessário:

```bash
cp .env.example .env
```

### Variáveis de ambiente

- `APP_NAME` - Nome da aplicação (padrão: labia-chat)
- `APP_ENV` - Ambiente (development/production)
- `APP_DEBUG` - Modo debug (true/false)
- `CORS_ALLOW_ORIGINS` - Origins permitidos (separados por vírgula)

## Execução

### Modo desenvolvimento (com reload automático)

```bash
cd backend
uvicorn labia_chat.main:app --reload
```

### Modo produção

```bash
cd backend
uvicorn labia_chat.main:app --host 0.0.0.0 --port 8000
```

## Testes

```bash
cd backend
pytest
```

## Linting

```bash
cd backend
ruff check .
```

## Endpoints

### GET /health

Verifica se o backend está operacional.

**Resposta:**
```json
{
  "status": "ok",
  "service": "labia-chat"
}