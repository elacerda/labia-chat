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
│       │       ├── health.py
│       │       └── auth.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   └── errors.py
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── user.py
│       └── services/
│           ├── __init__.py
│           ├── adss_client.py
│           └── auth_service.py
├── tests/
│   ├── test_health.py
│   ├── test_auth_route.py
│   └── test_auth_service.py
├── pyproject.toml
├── .env.example
└── README.md
```

## Ambiente pyenv

O backend espera o uso do ambiente virtual `labia-chat` gerenciado pelo pyenv.

Para entrar no backend e configurar o ambiente:

```bash
cd backend
pyenv local labia-chat
python --version
which python
```

A saída de `python --version` deve mostrar a versão configurada no ambiente `labia-chat`.
A saída de `which python` deve apontar para o Python dentro do pyenv.

## Instalação

Use sempre `python -m pip` para garantir que os pacotes sejam instalados no ambiente correto:

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

#### Configurações da aplicação

- `APP_NAME` - Nome da aplicação (padrão: `labia-chat`)
- `APP_ENV` - Ambiente (`development` ou `production`)
- `APP_DEBUG` - Modo debug (`true` ou `false`)

#### Configurações de CORS

- `CORS_ALLOW_ORIGINS` - Origins permitidos (separados por vírgula)

#### Configurações do ADSS (AI-Scope)

- `ADSS_BASE_URL` - URL base do serviço ADSS
- `ADSS_REQUIRED_ROLE` - Role obrigatória para acesso (padrão: `chat_vllm`)
- `ADSS_AUTH_CACHE_TTL_SECONDS` - Tempo de cache da autenticação em segundos (padrão: `300`)
  - **Nota:** Esta configuração está planejada, mas o cache de token ainda não foi implementado no MVP 1.
- `ADSS_TIMEOUT_SECONDS` - Timeout em segundos para requisições ao ADSS (padrão: `10`)

#### Configurações futuras (MVP 2+)

- `DATABASE_URL` - URL de conexão com banco de dados (MVP 2)
  - Exemplo: `DATABASE_URL=postgresql+asyncpg://labia_chat:labia_chat@localhost:5432/labia_chat`
- `VLLM_BASE_URL` - URL base do vLLM (MVP 4)
- `VLLM_DEFAULT_MODEL` - Modelo padrão do vLLM (MVP 4)

## Banco de Dados

O backend usa SQLAlchemy async com PostgreSQL para persistência de dados.

### Configuração

Copie o arquivo `.env.example` para `.env` e configure a variável `DATABASE_URL`:

```bash
cp .env.example .env
# Edite .env e configure sua DATABASE_URL
```

### Migrations

Para aplicar as migrations:

```bash
cd backend
python -m alembic upgrade head
```

Para criar uma nova migration:

```bash
cd backend
python -m alembic revision -m "nome_da_migration"
```

**Nota:** As tabelas de usuários/conversas/mensagens serão criadas nas próximas microtarefas.

## Execução

### Modo desenvolvimento (com reload automático)

```bash
cd backend
python -m uvicorn labia_chat.main:app --reload
```

O servidor estará disponível em `http://localhost:8000`.

### Modo produção

```bash
cd backend
python -m uvicorn labia_chat.main:app --host 0.0.0.0 --port 8000
```

## Testes

### Executar testes

```bash
cd backend
python -m pytest tests/ -v
```

### Executar lint

```bash
cd backend
python -m ruff check src/ tests/
```

## Endpoints

### GET /health

Verifica se o backend está operacional.

**Exemplo de requisição:**

```http
GET /health HTTP/1.1
```

**Resposta (200 OK):**

```json
{
  "status": "ok",
  "service": "labia-chat"
}
```

### GET /auth/me

Valida token AI-Scope e retorna usuário normalizado.

**Exemplo de requisição:**

```http
GET /auth/me HTTP/1.1
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

**Exemplo com curl:**

```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>"
```

**Funcionamento:**

1. O backend extrai o token do header `Authorization`
2. Valida o token no ADSS usando o endpoint `/users/me`
3. Verifica se `is_active == true`
4. Verifica se o usuário possui a role `chat_vllm`
5. Retorna um objeto `AuthenticatedUser` normalizado

**Códigos de resposta esperados:**

| Código | Descrição |
|--------|-----------|
| 200 | Token válido, usuário ativo e com role exigida |
| 401 | Header ausente/malformado ou token inválido/expirado |
| 403 | Usuário inativo ou sem role exigida |
| 503 | ADSS indisponível, timeout ou erro externo |

## Escopo atual do MVP 1

O MVP 1 foca na implementação da camada de autenticação e endpoints básicos. As seguintes funcionalidades **não** estão implementadas:

- **Banco de dados** - Não há persistência de dados
- **Sessão própria do labia-chat** - Não há gerenciamento de sessões
- **Refresh token** - Apenas access tokens são validados
- **Cookies** - Não há uso de cookies para autenticação
- **vLLM** - Não há integração com modelos de linguagem
- **Frontend novo** - O frontend atual está em `legacy/nextjs-prototype/`
- **Persistência de histórico** - Não há histórico de conversas

Estas funcionalidades estão planejadas para versões futuras (MVP 2+).