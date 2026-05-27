# 02 — Autenticação e autorização via AI-Scope

## Endpoint de validação do AI-Scope

O `labia-chat` valida tokens chamando:

```http
GET https://ai-scope.cbpf.br/adss/v1/users/me
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

Resposta esperada, conceitualmente:

```json
{
  "username": "teste",
  "email": "teste@teste.com",
  "full_name": "teste",
  "id": "beae96f3-a2b0-42c6-8b9d-fdc112177638",
  "is_active": true,
  "is_staff": false,
  "is_superuser": false,
  "roles": [
    {"name": "public", "description": "...", "id": 1},
    {"name": "chat_vllm", "description": "...", "id": 99}
  ]
}
```

## Regra de autorização

O usuário só pode usar o chat se:

```text
is_active == true
roles contém "chat_vllm"
```

A role exigida deve ser configurável:

```env
ADSS_REQUIRED_ROLE=chat_vllm
```

## MVP: token AI-Scope direto

No MVP inicial, o cliente envia o token do AI-Scope diretamente ao backend `labia-chat` em cada requisição protegida:

```http
Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>
```

O backend:

1. Extrai o Bearer token.
2. Valida no AI-Scope via `/users/me`.
3. Verifica `is_active`.
4. Verifica role `chat_vllm`.
5. Sincroniza usuário local.
6. Prossegue com a requisição.

## Testes manuais sem frontend

Como não haverá frontend no início, o token será obtido manualmente no AI-Scope e passado em chamadas via `curl`, `requests`, Swagger UI, Postman, Insomnia ou ferramentas similares.

Exemplo de chamada ao backend:

```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer <AI_SCOPE_ACCESS_TOKEN>"
```

## Cache curto de validação

Para evitar chamada ao AI-Scope em toda mensagem, o MVP pode ter cache curto:

```env
ADSS_AUTH_CACHE_TTL_SECONDS=300
```

Comportamento:

1. Primeira requisição com token: valida no AI-Scope.
2. Guarda resultado no cache por alguns minutos.
3. Próximas requisições com o mesmo token usam cache.
4. Após expirar o cache, revalida.

Recomendação: usar hash do token como chave de cache, evitando guardar o token cru.

## Erros esperados

### Token ausente ou inválido

```http
401 Unauthorized
```

Resposta conceitual:

```json
{
  "detail": "Invalid or missing AI-Scope token"
}
```

### Usuário sem role exigida

```http
403 Forbidden
```

Resposta conceitual:

```json
{
  "detail": "User does not have required role: chat_vllm"
}
```

## Fase futura: sessão própria do labia-chat

A fase futura pode adicionar:

```http
POST /auth/callback
```

Fluxo futuro:

1. Receber token AI-Scope.
2. Validar no AI-Scope.
3. Exigir role `chat_vllm`.
4. Criar sessão própria do `labia-chat`.
5. Retornar token/sessão própria ao frontend.

Essa fase não entra no MVP inicial.
