# 01 — Arquitetura proposta

## Visão arquitetural

Fluxo de alto nível:

```text
Usuário
  -> AI-Scope
    -> frontend futuro do chat
      -> labia-chat FastAPI
        -> PostgreSQL
        -> vLLM/OpenAI-compatible API
```

No MVP, ainda não há frontend. O desenvolvedor/testador chama o backend manualmente enviando um `access_token` do AI-Scope.

## Fronteiras do sistema

### AI-Scope

Responsável por:

- login do usuário;
- emissão de `access_token`;
- endpoint de validação `GET /adss/v1/users/me`;
- fonte de verdade para usuário, status ativo e roles.

### labia-chat FastAPI

Responsável por:

- validar token AI-Scope recebido nas requisições;
- exigir role `chat_vllm`;
- sincronizar dados mínimos do usuário localmente;
- persistir conversas e mensagens;
- escolher modelo disponível;
- chamar vLLM;
- transmitir resposta em streaming;
- expor endpoints para futuro frontend.

### vLLM

Responsável por:

- servir modelos locais via API OpenAI-compatible;
- responder chamadas de chat/completions;
- gerar streaming de tokens.

## Estrutura de diretórios sugerida

```text
backend/
  pyproject.toml
  README.md
  .env.example
  alembic.ini

  alembic/
    versions/

  src/
    labia_chat/
      __init__.py
      main.py

      api/
        deps.py
        routes/
          auth.py
          health.py
          models.py
          conversations.py
          chat.py

      core/
        config.py
        errors.py
        logging.py
        security.py

      db/
        base.py
        session.py

      models/
        user.py
        conversation.py
        message.py

      schemas/
        auth.py
        user.py
        model.py
        conversation.py
        chat.py

      services/
        adss_client.py
        auth_service.py
        model_registry.py
        vllm_client.py
        chat_service.py
        conversation_service.py

      repositories/
        users.py
        conversations.py
        messages.py

  tests/
    unit/
    integration/
```

## Princípios de desenho

1. O frontend nunca deve falar diretamente com o vLLM.
2. A API key do vLLM nunca deve ser exposta ao cliente.
3. O AI-Scope é a fonte de verdade para autenticação e autorização.
4. O `labia-chat` mantém apenas um espelho local mínimo dos usuários.
5. A lógica de chat, streaming, histórico e futuramente tool calling deve ficar no backend.
6. O sistema deve nascer preparado para múltiplos modelos.
7. O MVP deve evitar complexidade desnecessária, principalmente sessão própria e tool calling.
