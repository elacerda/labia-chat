# CLI de chat — especificação inicial

Data de referência: 2026-05-28  
Projeto: `labia-chat`

## 1. Objetivo

Criar um CLI de chat que exercite o backend como cliente real antes do início do frontend.

O CLI deve validar:

- autenticação via token AI-Scope;
- criação de conversa;
- envio de mensagem;
- geração persistente;
- leitura de histórico persistido;
- tratamento de erros reais do backend.

O CLI não deve chamar o vLLM diretamente. Toda geração deve passar pelo backend.

## 2. Fonte de verdade do histórico

A fonte de verdade de conversas e mensagens é sempre o backend/PostgreSQL.

O CLI não deve salvar mensagens localmente.

Estado local permitido:

- `api_url`;
- preferências não sensíveis;
- opcionalmente `last_conversation_id`.

Estado local proibido no MVP inicial:

- token salvo em texto claro;
- histórico de mensagens;
- senha AI-Scope;
- payloads completos de resposta com dados sensíveis.

## 3. Configuração inicial

### API URL

Precedência recomendada:

```text
flag CLI > variável de ambiente > arquivo de configuração > default
```

Default:

```text
http://127.0.0.1:8010
```

Variável:

```bash
LABIA_CHAT_API_URL=http://127.0.0.1:8010
```

Flag:

```bash
labia-chat chat --api-url http://127.0.0.1:8010
```

### Token

Precedência recomendada:

```text
flag CLI > variável de ambiente > prompt interativo sem eco
```

Variável:

```bash
LABIA_CHAT_TOKEN=<AI_SCOPE_ACCESS_TOKEN>
```

Flag:

```bash
labia-chat chat --token "$AI_SCOPE_ACCESS_TOKEN"
```

Prompt:

```text
AI-Scope token:
```

O prompt deve ocultar o token digitado.

## 4. Comando interativo mínimo

Comando principal:

```bash
labia-chat chat
```

Fluxo mínimo:

```text
1. Resolver api_url.
2. Resolver token.
3. Validar token em GET /auth/me.
4. Criar conversa em POST /chat/conversations.
5. Entrar no loop interativo.
6. Para cada mensagem:
   - chamar POST /chat/conversations/{id}/generate;
   - imprimir resposta assistant;
   - continuar até /exit.
```

Exemplo:

```text
Autenticado como: eduardo
Nova conversa criada: 50c592cf-2195-4d4d-a20b-cfc2aab951a7

Você: Explique supernovas tipo Ia em uma frase.
Assistente: Uma supernova tipo Ia é uma explosão termonuclear de uma anã branca em um sistema binário.

Você:
```

## 5. Comandos internos

MVP inicial:

```text
/help   mostra ajuda
/exit   sai do CLI
```

MVP seguinte:

```text
/new              cria nova conversa
/list             lista conversas recentes
/use <id>         troca de conversa
/history          recarrega mensagens da conversa atual
/whoami           mostra usuário autenticado
/clear            limpa tela local
```

## 6. Endpoints consumidos

MVP 2.11:

```http
GET  /auth/me
POST /chat/conversations
POST /chat/conversations/{conversation_id}/generate
```

MVP 2.12:

```http
GET /chat/conversations
GET /chat/conversations/{conversation_id}/messages
```

MVP 2.13:

```http
POST /chat/conversations
GET  /chat/conversations
GET  /chat/conversations/{conversation_id}/messages
POST /chat/conversations/{conversation_id}/generate
```

## 7. Tratamento de erros esperado

| Status | Interpretação | Mensagem CLI sugerida |
|--------|---------------|-----------------------|
| 401 | token ausente, inválido ou expirado | `Token inválido ou expirado. Gere um novo token AI-Scope.` |
| 403 | usuário sem role necessária | `Usuário autenticado, mas sem permissão chat_vllm.` |
| 404 | conversa inexistente ou sem ownership | `Conversa não encontrada para este usuário.` |
| 422 | payload inválido | `Entrada inválida. Verifique parâmetros e UUIDs.` |
| 502 | falha na geração/vLLM | `Backend não conseguiu obter resposta do modelo.` |

## 8. Login futuro

O MVP inicial não deve implementar login automático.

Evolução possível:

```bash
labia-chat login
```

Opções futuras:

1. colar token manualmente e validar com `/auth/me`;
2. chamar rota de login ADSS com usuário/senha, sem salvar senha;
3. abrir navegador/device flow, se o AI-Scope oferecer fluxo apropriado.

Armazenamento futuro de token só deve ser feito com mecanismo seguro, como keyring, e mediante decisão explícita.
