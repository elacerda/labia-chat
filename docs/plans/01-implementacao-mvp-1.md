# 01 — Implementação do primeiro MVP

Este documento detalha a primeira fatia de implementação recomendada.

## Nome do primeiro bloco

`MVP 0 + MVP 1 mínimo`: estrutura FastAPI + autenticação AI-Scope.

A recomendação é implementar em dois pequenos passos, mas no mesmo ciclo inicial:

1. Backend executável com health check.
2. Validação de token AI-Scope com `/auth/me`.

## Objetivo

Ter um backend FastAPI que sobe localmente, carrega `.env`, expõe `/health` e valida manualmente um `access_token` do AI-Scope em `/auth/me`.

Ainda não inclui banco, vLLM, conversas ou streaming.

## Dependências iniciais

Sugestão para `pyproject.toml`:

```text
fastapi
uvicorn[standard]
pydantic-settings
httpx
pytest
pytest-asyncio
respx
ruff
```

Banco/ORM ficam para o próximo bloco, para evitar misturar muitos riscos no primeiro patch.

## Estrutura inicial

```text
backend/
  pyproject.toml
  .env.example
  src/
    labia_chat/
      __init__.py
      main.py
      core/
        config.py
      api/
        deps.py
        routes/
          health.py
          auth.py
      schemas/
        user.py
      services/
        adss_client.py
        auth_service.py
  tests/
    test_health.py
    test_auth_service.py
```

## Configuração `.env.example`

```env
APP_NAME=labia-chat
APP_ENV=development
APP_DEBUG=true

ADSS_BASE_URL=https://ai-scope.cbpf.br/adss/v1
ADSS_REQUIRED_ROLE=chat_vllm
ADSS_AUTH_CACHE_TTL_SECONDS=300
ADSS_TIMEOUT_SECONDS=10
```

## Módulos

### `core/config.py`

Responsável por carregar configurações via Pydantic Settings.

Campos mínimos:

```text
app_name
app_env
app_debug
adss_base_url
adss_required_role
adss_auth_cache_ttl_seconds
adss_timeout_seconds
```

### `services/adss_client.py`

Responsável por chamar o AI-Scope:

```http
GET {ADSS_BASE_URL}/users/me
Authorization: Bearer <token>
```

Deve retornar payload normalizado ou lançar erro de autenticação.

### `services/auth_service.py`

Responsável por:

- receber token;
- chamar `AdssClient`;
- verificar `is_active`;
- verificar role exigida;
- normalizar roles;
- retornar usuário autenticado.

### `api/deps.py`

Responsável por dependency FastAPI:

```text
get_current_user
```

Essa dependency:

- extrai header `Authorization`;
- valida formato `Bearer`;
- chama `AuthService`;
- retorna usuário autorizado.

### `api/routes/auth.py`

Endpoint:

```http
GET /auth/me
```

Deve usar `get_current_user` e retornar usuário normalizado.

### `api/routes/health.py`

Endpoint:

```http
GET /health
```

Resposta:

```json
{"status": "ok"}
```

## Schema de usuário normalizado

```json
{
  "id": "beae96f3-a2b0-42c6-8b9d-fdc112177638",
  "username": "teste",
  "email": "teste@teste.com",
  "full_name": "teste",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "roles": ["public", "chat_vllm"]
}
```

## Comportamento esperado

### Token ausente

```http
401 Unauthorized
```

### Token inválido ou expirado

```http
401 Unauthorized
```

### Usuário inativo

```http
403 Forbidden
```

### Usuário sem role `chat_vllm`

```http
403 Forbidden
```

### Usuário válido

```http
200 OK
```

Com payload normalizado.

## Teste manual

### Obter token

```python
import requests

res = requests.post(
    "https://ai-scope.cbpf.br/adss/v1/auth/login",
    data={
        "username": "teste",
        "password": "asdflkjh",
    },
)

token = res.json()["access_token"]
print(token)
```

### Chamar backend

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>"
```

## Testes automatizados mínimos

### `test_health.py`

- `GET /health` retorna 200.
- Payload contém `status: ok`.

### `test_auth_service.py`

Usando mock do ADSS:

- token válido + role `chat_vllm` retorna usuário.
- token válido sem role `chat_vllm` falha com 403.
- token inválido falha com 401.
- usuário inativo falha com 403.

## Critério de pronto

Este primeiro MVP estará pronto quando:

- o backend sobe localmente;
- `/health` funciona;
- `/auth/me` valida token real do AI-Scope;
- `/auth/me` bloqueia usuário sem role `chat_vllm`;
- testes unitários básicos passam;
- `.env.example` documenta variáveis mínimas.

## Próximo bloco depois deste

Depois de concluir este MVP, o próximo bloco será:

```text
MVP 2 — PostgreSQL + SQLAlchemy 2 async + Alembic
```

Só então criaremos tabelas e persistência.
