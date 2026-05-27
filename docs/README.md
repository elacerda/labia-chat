# labia-chat — especificações do novo backend FastAPI

Este pacote contém a especificação inicial da nova versão do projeto `labia-chat`.

A direção definida é transformar o projeto em um backend Python/FastAPI para chat com modelos locais servidos por vLLM/OpenAI-compatible API, autorizado por token do AI-Scope e com histórico persistido em PostgreSQL.

## Conteúdo

- `specs/00-visao-geral.md` — visão geral, objetivos e decisões tomadas.
- `specs/01-arquitetura.md` — arquitetura proposta, fronteiras e estrutura de diretórios.
- `specs/02-autenticacao-ai-scope.md` — validação de token AI-Scope, role `chat_vllm` e estratégia de cache.
- `specs/03-banco-dados.md` — PostgreSQL, SQLAlchemy 2, Alembic e modelo conceitual de tabelas.
- `specs/04-modelos-vllm.md` — model registry, vLLM e desenho model-agnostic.
- `specs/05-endpoints.md` — endpoints planejados para auth, health, models, conversations e chat.
- `plans/00-plano-mvps.md` — plano completo de MVPs/fases.
- `plans/01-implementacao-mvp-1.md` — implementação detalhada do primeiro MVP.

## Escopo atual

O foco imediato é apenas o backend. O frontend será desenvolvido depois e provavelmente ficará no mesmo repositório.
