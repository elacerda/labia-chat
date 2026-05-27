# 00 — Visão geral do novo `labia-chat`

## Contexto

O projeto `labia-chat` deixa de ser uma aplicação centrada em Next.js/React e passa a ser um backend Python/FastAPI para fornecer serviço de chat autorizado pelo AI-Scope.

O frontend atual pode ser mantido temporariamente como referência visual/legado, mas o novo desenvolvimento começa pelo backend.

O frontend final será desenvolvido futuramente e deverá ser integrado ao AI-Scope, que é o portal onde o usuário já faz login.

## Objetivo principal

Construir um backend FastAPI que:

1. Recebe requisições autenticadas com `access_token` do AI-Scope.
2. Valida esse token consultando o endpoint `GET /adss/v1/users/me` do AI-Scope.
3. Permite uso apenas para usuários ativos com a role `chat_vllm`.
4. Usa o `id` retornado pelo AI-Scope como identificador do usuário nas tabelas locais.
5. Persiste histórico de conversas em PostgreSQL.
6. Encaminha mensagens para modelos locais servidos via vLLM/OpenAI-compatible API.
7. Retorna respostas em streaming para o cliente.
8. Nasce preparado para múltiplos modelos, mesmo que o MVP use apenas um.

## Decisões tomadas

- Backend: Python + FastAPI.
- Banco: PostgreSQL.
- ORM: SQLAlchemy 2 async.
- Migrações: Alembic.
- Cliente HTTP: httpx.
- Autenticação MVP: usar diretamente o token do AI-Scope em cada requisição protegida.
- Autorização MVP: exigir role `chat_vllm`.
- Sessão própria do `labia-chat`: fora do MVP inicial, possível fase futura.
- Tool calling: fora do MVP inicial.
- Frontend: fora do MVP inicial.
- Modelos: desenho model-agnostic, com provider inicial OpenAI-compatible/vLLM.

## Escopo explícito do MVP

Inclui:

- Estrutura FastAPI.
- `.env` e `.env.example`.
- Configuração por Pydantic Settings.
- Health check básico.
- Validação de token AI-Scope.
- Role obrigatória `chat_vllm`.
- Cache curto opcional de validação.
- PostgreSQL.
- SQLAlchemy 2 async.
- Alembic.
- Tabelas de usuários, conversas e mensagens.
- Model registry simples via `.env`.
- Cliente vLLM OpenAI-compatible.
- Endpoint de streaming de chat.
- CRUD básico de conversas.
- Testes manuais usando token AI-Scope passado no header.

Não inclui:

- Frontend novo.
- Sessão própria do `labia-chat`.
- Tool calling.
- Upload de arquivos.
- Multimodal.
- Admin UI.
- Feedback de respostas.
- Rate limiting avançado.
- Observabilidade completa.
