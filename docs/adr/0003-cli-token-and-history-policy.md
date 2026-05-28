# ADR 0003 — Política de token e histórico no CLI

Data: 2026-05-28  
Status: Proposto

## Contexto

O CLI precisa autenticar chamadas ao backend com token AI-Scope. Também precisa exibir histórico de conversa.

Tokens são segredos. Histórico de mensagens pertence ao domínio da aplicação e já é persistido pelo backend.

## Decisão

1. O CLI não salva token em texto claro no MVP inicial.
2. O CLI aceita token por flag, variável de ambiente ou prompt sem eco.
3. O backend/PostgreSQL é a única fonte de verdade para histórico de conversas e mensagens.
4. O CLI não salva mensagens localmente.
5. Estado local opcional pode guardar apenas preferências não sensíveis e `last_conversation_id`.

## Precedência de configuração

Para API URL:

```text
flag > env > config file > default
```

Para token:

```text
flag > env > prompt
```

## Consequências positivas

- Menor risco de exposição de token.
- Histórico consistente entre CLI e futuro frontend.
- Menos lógica local.
- Menos risco de divergência entre clientes.

## Consequências negativas

- Usuário precisa fornecer token com frequência.
- Retomada de sessão é menos conveniente no MVP inicial.
- Login seguro fica para uma etapa posterior.

## Evolução futura

Uma etapa futura pode implementar:

- `labia-chat login`;
- integração com rota de login ADSS;
- armazenamento seguro via keyring;
- device/browser flow, se disponível.
