# 09 — Limitações Conhecidas e Fora de Escopo

## Limitações atuais

### CLI

O CLI é útil para desenvolvimento, validação operacional e pilotos técnicos, mas ainda não é uma interface final para qualquer usuário não técnico.

Limitações:

- requer token manual;
- não possui `labia-chat login`;
- não salva sessão;
- não possui empacotamento de distribuição;
- exige familiaridade com terminal.

### Paginação

A paginação atual é `limit/offset`.

Fora do escopo atual:

- cursor pagination;
- contagem total;
- metadata de paginação;
- wrappers de resposta;
- filtros por data;
- busca textual.

### Modelo

A integração com modelo depende de vLLM OpenAI-compatible disponível.

Fora do escopo atual:

- streaming;
- seleção dinâmica de modelo por usuário;
- fallback automático;
- tools/function calling;
- RAG;
- upload de arquivos.

### Frontend

Frontend ainda não está coberto por este pacote.

Não assumir que o próximo roadmap é frontend. O próximo roadmap será definido por instrução posterior.

## O que não fazer automaticamente

Não iniciar nenhuma destas frentes sem instrução explícita:

- frontend;
- login automático;
- persistência local de token;
- keyring;
- websocket;
- streaming;
- RAG;
- upload;
- alteração de schema;
- autenticação alternativa;
- refatoração ampla de backend.
