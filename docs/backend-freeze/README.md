# Backend Freeze — labia-chat

Data de referência: 2026-05-28  
Projeto: `labia-chat`  
Estratégia vigente: backend-first  
Estado: backend + CLI em congelamento operacional inicial após MVP 2.16

Este diretório reúne a documentação de handoff para outro programador ou agente de IA continuar o projeto sem reabrir decisões já estabilizadas do backend.

## Como ler este pacote

1. Leia `00-backend-freeze-status.md` para entender o estado congelado.
2. Leia `01-api-contract.md` para conhecer o contrato REST.
3. Leia `02-cli-contract.md` para conhecer o cliente CLI.
4. Leia `03-environment-and-runbook.md` para subir e validar o ambiente.
5. Leia `04-smoke-validation.md` para executar validação operacional.
6. Leia `05-security-and-secrets.md` antes de tocar em tokens, `.env` ou logs.
7. Leia `06-change-policy-after-freeze.md` antes de alterar backend.
8. Use `07-agent-handoff-prompt.md` como prompt base para outro agente/modelo.
9. Use `08-backend-freeze-checklist.md` como checklist de aceite.

## Escopo deste congelamento

O congelamento cobre:

- backend FastAPI;
- autenticação via AI-Scope/ADSS;
- persistência de conversas e mensagens;
- geração via vLLM OpenAI-compatible;
- CLI operacional;
- paginação e limites de listagem;
- smoke validation core e com modelo.

O congelamento não cobre:

- frontend;
- login automático;
- streaming;
- websocket;
- RAG;
- upload;
- tools/function calling;
- empacotamento de CLI para usuário final.

## Observação de roadmap

Este pacote não define o próximo roadmap. A próxima etapa será definida por instrução posterior.
