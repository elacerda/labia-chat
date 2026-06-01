# 04 — Smoke Validation

Script:

```bash
backend/scripts/smoke_cli.sh
```

## Objetivo

Validar operacionalmente o backend e o CLI sem depender de frontend.

## Requisitos

- backend rodando em `LABIA_CHAT_API_URL`, default `http://127.0.0.1:8010`;
- token válido em `LABIA_CHAT_TOKEN`;
- vLLM rodando somente para `--with-model`.

## Preparar token

Não cole token em comandos inline. Use:

```bash
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo
```

## Smoke core

```bash
bash backend/scripts/smoke_cli.sh
```

Valida:

1. `GET /health`;
2. `labia-chat auth me`;
3. `labia-chat conversations create`;
4. `labia-chat conversations list --limit 5 --offset 0`;
5. `labia-chat messages list <conversation-id> --limit 10 --offset 0`;
6. `labia-chat config init` e `labia-chat config show` (configuração local não sensível);
7. arquivo de configuração existe e não contém segredos (token, Bearer, Authorization, etc).

Observação:

- para conversa recém-criada, `Nenhuma mensagem ainda.` é saída esperada;
- esse caso deve ser tratado como sucesso se o comando sair com exit code `0`;
- o script cria um diretório temporário para configuração e o remove ao final.

## Smoke com modelo

```bash
bash backend/scripts/smoke_cli.sh --with-model
```

Valida também:

8. `labia-chat chat send <conversation-id> "Responda apenas com: SMOKE_OK"`;
9. `labia-chat messages list <conversation-id> --limit 10 --offset 0`;
10. `POST /chat/model/ping`.

Critério correto:

- `chat send` passa se o comando retorna exit code `0` e saída não vazia;
- o conteúdo do modelo não deve ser validado semanticamente;
- o modelo pode ou não obedecer exatamente `SMOKE_OK`;
- o script pode exibir preview da resposta, mas não deve depender de texto fixo.

## Último resultado reportado

Smoke `--with-model` passou com:

```text
Step 1: GET /health — PASS
Step 2: labia-chat auth me — PASS
Step 3: create conversation — PASS
Step 4: list conversations — PASS
Step 5: list messages empty — PASS
Step 6: chat send — PASS
Step 7: list messages with message — PASS
Step 8: model ping — PASS
Summary: All checks passed
```

## Uso com API URL customizada

```bash
bash backend/scripts/smoke_cli.sh --api-url http://127.0.0.1:8010
bash backend/scripts/smoke_cli.sh --api-url http://127.0.0.1:8010 --with-model
```

## Configuração local (não sensível)

O smoke validation agora cria um diretório temporário para configuração do CLI e valida:

- `labia-chat config init` salva apenas valores não sensíveis (`api_url`, `streaming_default`, `show_last_default`);
- `labia-chat config show` exibe a configuração resolvida sem expor tokens;
- o arquivo `config.toml` não deve conter chaves como `token`, `Bearer`, `Authorization`, `LABIA_CHAT_TOKEN`, `AI_SCOPE_ACCESS_TOKEN`, `VLLM_API_KEY` ou `DATABASE_URL`.