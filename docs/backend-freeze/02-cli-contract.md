# 02 — Contrato do CLI

Entry point:

```bash
labia-chat
```

O CLI é o cliente real temporário para validar o backend antes do frontend.

## Configuração

API URL:

```text
1. --api-url
2. LABIA_CHAT_API_URL
3. default http://127.0.0.1:8010
```

Token:

```text
1. --token
2. LABIA_CHAT_TOKEN
3. prompt sem eco via getpass.getpass()
```

O CLI não deve:

- salvar token;
- salvar histórico local;
- imprimir token;
- criar configuração persistente de credenciais nesta fase.

## Comandos principais

### Auth

```bash
labia-chat auth me
```

Valida token e usuário.

### Criar conversa

```bash
labia-chat conversations create --title "Teste"
```

### Listar conversas

```bash
labia-chat conversations list --limit 20 --offset 0
```

Regras:

- `limit` default: `20`;
- `offset` default: `0`;
- backend impõe máximo `100`.

### Listar mensagens

```bash
labia-chat messages list <conversation-id> --limit 50 --offset 0
```

Regras:

- `limit` default: `50`;
- `offset` default: `0`;
- backend impõe máximo `200`;
- conversa sem mensagens deve exibir mensagem amigável como `Nenhuma mensagem ainda.` e sair com exit code `0`.

### Enviar mensagem não interativa

```bash
labia-chat chat send <conversation-id> "mensagem"
```

Esse comando valida o fluxo de geração persistente e depende de vLLM disponível.

### Chat interativo

```bash
labia-chat chat
labia-chat chat --conversation-id <uuid>
labia-chat chat --conversation-id <uuid> --show-last 10
```

Comandos internos:

```text
/help
/history
/exit
```

## Público-alvo atual do CLI

O CLI está adequado para:

- desenvolvimento;
- smoke test;
- inspeção operacional;
- pilotos técnicos;
- validação de backend.

O CLI ainda não é uma interface final para qualquer usuário não técnico.

Limitações atuais:

- requer token manual;
- não possui `labia-chat login`;
- não salva sessão;
- não possui empacotamento de distribuição;
- exige familiaridade com terminal.
