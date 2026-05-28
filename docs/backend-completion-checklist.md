# Checklist de fechamento do backend

Data de referência: 2026-05-28  
Projeto: `labia-chat`

Este checklist define o que precisa estar pronto antes de declarar o backend suficientemente fechado para início do frontend.

## 1. Funcionalidade core

- [ ] `GET /health` funcionando.
- [ ] `GET /auth/me` validando token AI-Scope/ADSS.
- [ ] Usuário autenticado sincronizado em `chat_users`.
- [ ] Conversas persistidas por usuário.
- [ ] Mensagens persistidas por conversa.
- [ ] Ownership validado em todos os endpoints de conversa/mensagem.
- [ ] `POST /chat/model/ping` funcionando como diagnóstico.
- [ ] `POST /chat/conversations/{conversation_id}/generate` persistindo mensagem `user` e mensagem `assistant`.

## 2. CLI

- [ ] CLI instalável por entrypoint.
- [ ] `labia-chat chat` funcionando em modo interativo.
- [ ] Token recebido por flag, env ou prompt sem eco.
- [ ] `api_url` recebido por flag/env/default.
- [ ] CLI valida `GET /auth/me`.
- [ ] CLI cria conversa.
- [ ] CLI envia mensagens via `/generate`.
- [ ] CLI imprime resposta `assistant`.
- [ ] CLI possui `/help` e `/exit`.
- [ ] CLI não salva histórico local.
- [ ] CLI não salva token em texto claro.

## 3. Histórico

- [ ] Backend é a única fonte de verdade para mensagens.
- [ ] CLI consegue listar conversas recentes.
- [ ] CLI consegue abrir conversa existente.
- [ ] CLI consegue listar mensagens da conversa.
- [ ] Estado local, se existir, guarda no máximo `last_conversation_id` e preferências não sensíveis.

## 4. Contrato de API

- [ ] Endpoints documentados.
- [ ] Schemas públicos documentados.
- [ ] Campos internos, como `user_id`, não vazam em respostas públicas.
- [ ] Erros principais documentados.
- [ ] Paginação definida para conversas e mensagens.
- [ ] Limites máximos definidos para payloads.

## 5. Erros e robustez

- [ ] 401 tratado de forma clara.
- [ ] 403 tratado de forma clara.
- [ ] 404 tratado de forma clara.
- [ ] 422 tratado de forma clara.
- [ ] 502 tratado de forma clara.
- [ ] Timeout vLLM configurável.
- [ ] Falha vLLM após mensagem `user` persistida está documentada ou possui fluxo de recuperação.
- [ ] Testes cobrem falhas críticas.

## 6. Segurança

- [ ] Nenhum token real em docs.
- [ ] Nenhuma senha real em docs.
- [ ] Nenhuma `DATABASE_URL` real com senha em docs.
- [ ] `.env` ignorado pelo git.
- [ ] `.env.example` contém apenas placeholders seguros.
- [ ] Logs não imprimem `Authorization`.
- [ ] Logs não imprimem `VLLM_API_KEY`.
- [ ] CORS revisado antes do frontend.

## 7. Observabilidade

- [ ] Logs básicos de autenticação sem segredo.
- [ ] Logs de geração sem prompt completo, se houver risco.
- [ ] Tempo de chamada ao vLLM registrado.
- [ ] Erros do vLLM mapeados para resposta pública segura.
- [ ] Request id/correlation id decidido ou implementado.

## 8. Testes

- [ ] `python -m pytest tests/ -v` passando.
- [ ] `python -m ruff check src/ tests/` passando.
- [ ] `python -m alembic current` apontando para head.
- [ ] Testes unitários de services principais.
- [ ] Testes HTTP de endpoints principais.
- [ ] Testes de CLI.
- [ ] Smoke test real documentado.

## 9. Documentação

- [ ] README atualizado com estado real do projeto.
- [ ] `backend/docs/chat-backend.md` atualizado.
- [ ] `docs/roadmap-backend-to-frontend.md` atualizado.
- [ ] `docs/cli-chat.md` atualizado.
- [ ] `docs/frontend-handoff.md` atualizado.
- [ ] Comandos de operação local documentados.
- [ ] Troubleshooting documentado.

## 10. Critério de backend freeze

O backend pode ser congelado para início do frontend quando:

- CLI interativo e não interativo validarem o fluxo real;
- documentação do contrato estiver clara;
- falhas principais tiverem mensagens previsíveis;
- testes automatizados passarem;
- smoke test real for reproduzível;
- frontend puder ser desenvolvido sem consultar detalhes internos do backend.
