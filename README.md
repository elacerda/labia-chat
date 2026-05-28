# labia-chat

Backend FastAPI para chat com modelos locais servidos via vLLM, integrado à autenticação do AI-Scope.

## Estado do projeto

Este repositório está sendo reestruturado.

- O projeto Next.js original foi preservado em `legacy/nextjs-prototype/`.
- O novo backend será desenvolvido em `backend/`.
- As especificações atuais estão em `docs/specs/`.
- O plano de MVPs está em `docs/plans/`.

## MVP atual

O primeiro MVP implementará:

- backend FastAPI;
- configuração via `.env`;
- endpoint `/health`;
- validação de token do AI-Scope;
- autorização por role `chat_vllm`;
- teste manual com `access_token`.

Veja `docs/plans/01-implementacao-mvp-1.md`.

## Documentação do Backend de Chat

Para documentação operacional completa do backend de chat (como rodar, testar endpoints, variáveis de ambiente, troubleshooting), veja:

**[backend/docs/chat-backend.md](backend/docs/chat-backend.md)**

Esta documentação cobre:

- Visão geral do fluxo completo (AI-Scope → backend → vLLM → persistência)
- Variáveis de ambiente (DATABASE_URL, VLLM_*, ADSS_*)
- Avisos de segurança (tokens, credenciais)
- Como rodar o backend
- Como testar endpoints via curl
- Problemas comuns e soluções
