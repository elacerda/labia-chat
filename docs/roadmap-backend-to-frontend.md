# Roadmap atualizado — do backend atual ao frontend e finalização

Data de referência: 2026-05-28  
Projeto: `labia-chat`  
Repositório: `elacerda/labia-chat`

## 1. Estado atual

O projeto já possui um backend FastAPI funcional para o fluxo mínimo de chat persistente:

- autenticação via token AI-Scope/ADSS;
- sincronização do usuário autenticado em banco local;
- persistência de usuários, conversas e mensagens em PostgreSQL;
- endpoints REST básicos de conversa e mensagem;
- integração com vLLM OpenAI-compatible;
- endpoint diagnóstico `POST /chat/model/ping`;
- endpoint real de geração persistente `POST /chat/conversations/{conversation_id}/generate`;
- documentação operacional em `backend/docs/chat-backend.md`.

O frontend ainda não deve ser iniciado como prioridade. A decisão atual do projeto é finalizar o backend antes de transferir o trabalho para uma pessoa desenvolvedora de frontend.

## 2. Decisão de direção

Antes do frontend, o projeto deve criar um CLI de chat suficientemente bom para validar o backend como um cliente real.

O CLI deve:

- chamar apenas o backend, nunca o vLLM diretamente;
- usar o backend como fonte de verdade para histórico;
- não persistir mensagens localmente;
- aceitar token por flag, variável de ambiente ou prompt sem eco;
- permitir um loop interativo mínimo de conversa;
- servir como ferramenta de smoke test e diagnóstico operacional.

## 3. Roadmap backend-first

### MVP 2.11 — CLI interativo mínimo

Objetivo: criar um cliente real de terminal para exercitar o fluxo completo do backend.

Escopo mínimo:

- entrypoint CLI instalável;
- comando `labia-chat chat`;
- configuração de `api_url` por flag, env ou default;
- token por flag, env ou prompt sem eco;
- validação inicial via `GET /auth/me`;
- criação de conversa via `POST /chat/conversations`;
- envio de mensagens via `POST /chat/conversations/{conversation_id}/generate`;
- impressão da resposta `assistant`;
- comandos internos `/help` e `/exit`.

Fora de escopo:

- salvar token localmente;
- login automático ADSS;
- histórico local;
- seleção de conversas existentes;
- comandos não interativos;
- streaming.

### MVP 2.12 — Histórico e retomada de conversa no CLI

Objetivo: permitir que o CLI use o histórico persistido no backend.

Escopo:

- listar conversas recentes via `GET /chat/conversations`;
- selecionar conversa existente;
- abrir conversa por `--conversation-id`;
- buscar mensagens via `GET /chat/conversations/{conversation_id}/messages`;
- mostrar últimas N mensagens ao abrir conversa;
- comando interno `/history`;
- opcionalmente salvar apenas `last_conversation_id` em estado local.

Regra: mensagens continuam persistidas apenas no backend.

### MVP 2.13 — CLI não interativo para smoke tests

Objetivo: permitir automação e diagnóstico sem entrar no loop interativo.

Comandos sugeridos:

```bash
labia-chat auth me
labia-chat conversations list
labia-chat conversations create --title "Teste"
labia-chat messages list <conversation-id>
labia-chat chat send <conversation-id> "mensagem"
```

### MVP 2.14 — Hardening de erros e UX operacional

Objetivo: transformar os problemas encontrados pelo CLI em melhorias no backend e no cliente.

Escopo:

- mensagens claras para 401, 403, 404, 422 e 502;
- timeouts configuráveis;
- tratamento de falha vLLM após persistência da mensagem `user`;
- padronização de erros públicos;
- testes de regressão.

### MVP 2.15 — Paginação e limites

Objetivo: tornar a API adequada para clientes reais.

Escopo:

- `limit` e `offset` ou cursor em listagem de conversas;
- `limit` e `offset` ou cursor em listagem de mensagens;
- limites máximos;
- ordenação explícita;
- documentação do contrato.

**Status:** Concluído

Contrato da API:

| Endpoint | Parâmetros | Padrão | Máximo |
|----------|------------|--------|--------|
| `GET /chat/conversations` | `limit`, `offset` | `limit=20`, `offset=0` | `limit=100` |
| `GET /chat/conversations/{id}/messages` | `limit`, `offset` | `limit=50`, `offset=0` | `limit=200` |

Validações:

- `limit >= 1`, `offset >= 0`
- Valores inválidos retornam HTTP 422
- Conversas ordenadas do mais recente para o mais antigo
- Mensagens ordenadas cronologicamente

CLI:

```bash
labia-chat conversations list --limit 20 --offset 0
labia-chat messages list <conversation-id> --limit 50 --offset 0
```

### MVP 2.16 — Operações de conversa

Objetivo: completar o ciclo de vida básico de conversas.

Escopo:

- renomear conversa;
- arquivar/desarquivar, se necessário;
- título automático após primeira mensagem, se decidido;
- testes de ownership.

### MVP 2.17 — Observabilidade mínima

Objetivo: facilitar diagnóstico em uso real.

Escopo:

- logs estruturados;
- request id/correlation id;
- tempo de chamada ao ADSS;
- tempo de chamada ao vLLM;
- logs sem tokens;
- eventos básicos de geração.

### MVP 2.18 — Testes de integração

Objetivo: validar fluxo realista com banco e, opcionalmente, vLLM.

Escopo:

- testes com banco real de teste;
- fixtures de usuário/conversa;
- teste ponta a ponta de conversa + geração;
- testes opcionais marcados como integração;
- documentação de execução.

### MVP 2.19 — Segurança e hardening

Objetivo: preparar backend para handoff seguro.

Escopo:

- revisão de CORS;
- revisão de vazamento de campos internos;
- garantia de ownership em todos os endpoints;
- tamanho máximo de payload;
- auditoria de logs;
- revisão de `.env.example`.

### MVP 2.20 — Documentação e DX final do backend

Objetivo: deixar outro desenvolvedor pronto para consumir a API.

Escopo:

- README atualizado;
- documentação do CLI;
- documentação da API;
- troubleshooting consolidado;
- comandos de smoke test;
- checklist de handoff.

### MVP 2.21 — Preparação de deploy local/ambiente

Objetivo: documentar e validar o caminho operacional.

Escopo:

- healthchecks;
- migrations;
- variáveis por ambiente;
- comando de startup;
- docker/docker-compose, se decidido;
- documentação de operação.

### MVP 2.22 — Backend freeze e handoff para frontend

Objetivo: congelar o contrato mínimo do backend para início do frontend.

Critérios:

- CLI interativo funcionando;
- CLI não interativo cobrindo smoke tests;
- API documentada;
- erros padronizados;
- ownership testado;
- paginação básica implementada;
- documentação de configuração pronta;
- nenhum segredo em docs;
- suíte automatizada passando.

## 4. Roadmap de frontend depois do backend freeze

### MVP 3.0 — Skeleton frontend

Criar app web mínimo somente depois do backend freeze.

### MVP 3.1 — Configuração de token e API URL

Tela simples para colar token e validar `GET /auth/me`.

### MVP 3.2 — Conversas e mensagens

Listar, criar e abrir conversas usando API estável.

### MVP 3.3 — Envio de mensagem

Enviar mensagem via `/generate` e renderizar resposta persistida.

### MVP 3.4 — UX mínima

Loading, erros, histórico e responsividade básica.

### MVP 3.5 — Handoff de produto

Ajustes de interface, documentação de frontend e validação ponta a ponta.

## 5. Finalização do projeto

O projeto pode ser considerado finalizado em uma primeira versão quando:

- backend e CLI estiverem estáveis;
- frontend mínimo consumir a API sem gambiarras;
- smoke test ponta a ponta estiver documentado;
- deploy local/ambiente estiver documentado;
- docs estiverem atualizadas;
- secrets não estiverem presentes no repositório;
- próximos escopos avançados estiverem explicitamente fora da versão inicial.
