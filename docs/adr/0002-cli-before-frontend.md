# ADR 0002 — Priorizar CLI antes do frontend

Data: 2026-05-28  
Status: Proposto

## Contexto

O backend do `labia-chat` já possui o fluxo mínimo de chat persistente: autenticação ADSS, persistência local, integração vLLM e endpoint `/generate`.

Um skeleton de frontend foi iniciado experimentalmente, mas a decisão atual é finalizar o backend antes de iniciar o desenvolvimento visual.

## Decisão

Priorizar a criação de um CLI de chat antes do frontend.

O CLI será usado como cliente real para validar:

- autenticação;
- criação de conversa;
- envio de mensagens;
- persistência de histórico;
- respostas do modelo;
- erros operacionais;
- contrato público da API.

## Consequências positivas

- Menor complexidade que frontend.
- Debug mais rápido.
- Validação real do backend.
- Ferramenta útil para smoke tests.
- Facilita handoff para frontend no futuro.
- Evita decisões prematuras de UX visual.

## Consequências negativas

- Não valida experiência web.
- Não valida CORS/navegador.
- Não substitui frontend final.

## Escopo inicial

O CLI inicial deve ser simples:

- token por flag/env/prompt;
- API URL por flag/env/default;
- modo interativo;
- criação de conversa;
- envio via `/generate`;
- `/help` e `/exit`.

## Fora de escopo

- salvar token localmente;
- login automático ADSS;
- streaming;
- histórico local;
- UI web.
