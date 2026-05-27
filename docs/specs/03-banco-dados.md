# 03 — Banco de dados, ORM e migrações

## Banco

O projeto usará PostgreSQL.

Configuração via `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/labia_chat
```

## ORM escolhido

Escolha recomendada:

```text
SQLAlchemy 2 async
```

Motivos:

- compatível com FastAPI e padrões async;
- robusto para serviço institucional;
- tipagem moderna com `Mapped[...]`;
- bom suporte a PostgreSQL;
- ecossistema maduro;
- bom encaixe com Alembic para migrações.

## Migrações

Ferramenta:

```text
Alembic
```

Uso previsto:

```bash
alembic revision -m "create chat tables"
alembic upgrade head
```

## Modelo conceitual

### `chat_users`

Espelho/cache local do usuário vindo do AI-Scope.

```text
id              text/uuid primary key  # id vindo do AI-Scope
username        text
email           text nullable
full_name       text nullable
is_active       boolean
is_staff        boolean
is_superuser    boolean
roles           jsonb
last_seen_at    timestamp with time zone
created_at      timestamp with time zone
updated_at      timestamp with time zone
```

Observação: o AI-Scope permanece a fonte de verdade. Esta tabela serve para associar histórico ao usuário e evitar depender do payload completo a cada consulta de conversas.

### `chat_conversations`

```text
id              uuid primary key
user_id         text/uuid foreign key -> chat_users.id
title           text
model_id        text
system_prompt   text nullable
created_at      timestamp with time zone
updated_at      timestamp with time zone
archived_at     timestamp with time zone nullable
```

### `chat_messages`

```text
id                uuid primary key
conversation_id   uuid foreign key -> chat_conversations.id
role              text  # system/user/assistant/tool
content           text
sequence_index    integer
model_id          text nullable
metadata          jsonb
created_at        timestamp with time zone
```

Papéis previstos:

```text
system
user
assistant
tool
```

No MVP, `tool` pode existir como valor previsto, mas tool calling não será implementado.

## Sessões locais

Tabela de sessão local do `labia-chat` fica fora do MVP inicial.

Fase futura possível:

```text
chat_sessions
  id
  user_id
  token_hash
  expires_at
  revoked_at
  created_at
  last_used_at
```

## Princípios de acesso a dados

- Usar repositories para encapsular queries.
- Usar services para regras de negócio.
- Rotas FastAPI não devem conter SQL diretamente.
- Toda conversa deve ser filtrada por `user_id` autenticado.
- `DELETE /conversations/{id}` deve preferencialmente fazer soft delete usando `archived_at`.
