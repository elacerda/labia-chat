# 05 — Segurança e Segredos

## Nunca commitar

Nunca commitar ou colar em issue/chat/PR:

- token AI-Scope real;
- `VLLM_API_KEY` real;
- `DATABASE_URL` real com senha;
- dumps contendo credenciais;
- logs com bearer token;
- `.env` real.

## Token AI-Scope

Forma recomendada para sessão local:

```bash
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo
```

Evitar:

```bash
export LABIA_CHAT_TOKEN=token-real-aqui
```

Esse comando pode ficar no histórico do shell.

## CLI

O CLI não deve:

- persistir token;
- imprimir token;
- salvar histórico local;
- criar cache de credenciais.

## Smoke script

O smoke script deve:

- exigir `LABIA_CHAT_TOKEN`;
- nunca imprimir o valor do token;
- mostrar apenas estado como `[SET - not shown]`;
- falhar se o token não estiver definido;
- não usar token inline em exemplos.

## Erros

Mensagens de erro devem ser amigáveis e não revelar detalhes sensíveis.

Matriz consolidada:

| Caso | Mensagem |
|---|---|
| 401 | `Token inválido ou expirado. Gere um novo token AI-Scope.` |
| 403 | `Usuário autenticado, mas sem permissão chat_vllm.` |
| 404 | `Conversa não encontrada para este usuário.` |
| 422 | `Dados inválidos. Verifique a entrada e tente novamente.` |
| timeout | `Timeout ao conectar ao backend. Tente novamente.` |
| rede | `Falha de conexão com o backend. Verifique sua rede.` |
| payload inesperado | `Resposta inesperada do backend. Tente novamente.` |
