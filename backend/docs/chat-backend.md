# Backend de Chat - Documentação Operacional

## Visão Geral do Fluxo

O fluxo completo de chat envolve os seguintes componentes:

```
AI-Scope Token → labia-chat Backend → Validação ADSS → Persistência Local → vLLM → Resposta Assistant
```

### 1. AI-Scope Token

O fluxo começa com um token de acesso do AI-Scope (ADSS). Este token deve ser enviado no header `Authorization: Bearer <token>` em todas as requisições protegidas.

### 2. Backend `labia-chat`

O backend FastAPI recebe as requisições, valida o token e coordena a geração de respostas.

### 3. Validação ADSS

O backend valida o token no serviço ADSS (`https://ai-scope.cbpf.br/adss/v1`) verificando:

- Token válido e não expirado
- Usuário ativo (`is_active == true`)
- Usuário possui a role `chat_vllm`

### 4. Persistência Local

As conversas e mensagens são persistidas em um banco de dados PostgreSQL usando SQLAlchemy async.

### 5. Chamada ao vLLM

O backend chama o servidor vLLM (OpenAI-compatible) para gerar a resposta do assistente usando o modelo configurado.

### 6. Persistência da Resposta Assistant

A resposta gerada é persistida como uma mensagem `assistant` com o campo `model` preenchido com o nome do modelo usado.

---

## Variáveis de Ambiente

### Configurações da Aplicação

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `APP_NAME` | `labia-chat` | Nome da aplicação |
| `APP_ENV` | `development` | Ambiente (`development` ou `production`) |
| `APP_DEBUG` | `true` | Modo debug (`true` ou `false`) |

### Configurações de CORS

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CORS_ALLOW_ORIGINS` | `http://localhost:3000,https://ai-scope.cbpf.br` | Origins permitidos (separados por vírgula) |

### Configurações do ADSS (AI-Scope)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ADSS_BASE_URL` | `https://ai-scope.cbpf.br/adss/v1` | URL base do serviço ADSS |
| `ADSS_REQUIRED_ROLE` | `chat_vllm` | Role obrigatória para acesso |
| `ADSS_AUTH_CACHE_TTL_SECONDS` | `300` | Tempo de cache da autenticação em segundos |
| `ADSS_TIMEOUT_SECONDS` | `10` | Timeout em segundos para requisições ao ADSS |

### Configurações do Banco de Dados (MVP 2+)

| Variável | Exemplo | Descrição |
|----------|---------|-----------|
| `DATABASE_URL` | `postgresql+asyncpg://labia_chat:labia_chat@localhost:5432/labia_chat` | URL de conexão com PostgreSQL |

### Configurações do vLLM (MVP 4+)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VLLM_BASE_URL` | `http://127.0.0.1:8000` | URL base do servidor vLLM |
| `VLLM_MODEL` | `qwen-coder-next` | Nome do modelo a ser usado |
| `VLLM_TIMEOUT_SECONDS` | `30` | Timeout em segundos para requisições ao vLLM |
| `VLLM_API_KEY` | *opcional* | API key para autenticação no vLLM |

### Configurações de Geração (MVP 5+)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `VLLM_TEMPERATURE` | `0.0` | Temperatura para geração (0.0 a 1.0) |
| `VLLM_MAX_TOKENS` | `512` | Número máximo de tokens a gerar |

---

## Avisos de Segurança

⚠️ **NUNCA** commite arquivos com valores sensíveis!

### Tokens e Credenciais Sensíveis

| Valor | Onde configurar | Risco se exposto |
|-------|-----------------|------------------|
| `AI_SCOPE_ACCESS_TOKEN` | `backend/.env` local | Acesso não autorizado ao AI-Scope |
| `VLLM_API_KEY` | `backend/.env` local | Acesso não autorizado ao vLLM |
| `DATABASE_URL` | `backend/.env` local | Acesso não autorizado ao banco de dados |

### Boas Práticas

1. **Nunca commite tokens reais** - Use valores de exemplo ou placeholders
2. **Mantenha `backend/.env` no `.gitignore`** - O arquivo `.env` já está configurado para ser ignorado
3. **Use variáveis de ambiente no deploy** - Não compartilhe arquivos `.env` entre ambientes
4. **Revogue tokens comprometidos** - Se um token for exposto, revogue-o imediatamente

---

## Como Rodar o Backend

### Pré-requisitos

- Python 3.11+
- PostgreSQL (para persistência)
- vLLM rodando localmente ou em servidor acessível

### Passos

```bash
cd backend

# Configurar ambiente pyenv (opcional, mas recomendado)
pyenv local labia-chat
python --version

# Instalar dependências
python -m pip install -e ".[dev]"

# Copiar arquivo de exemplo e ajustar variáveis
cp .env.example .env
# Edite .env e configure suas variáveis (especialmente DATABASE_URL e VLLM_API_KEY)

# Aplicar migrations
python -m alembic upgrade head

# Rodar o servidor
python -m uvicorn labia_chat.main:app --reload --host 127.0.0.1 --port 8010
```

O servidor estará disponível em `http://127.0.0.1:8010`.

---

## Como Verificar Saúde

### Health Check do Backend

```bash
curl -s http://127.0.0.1:8010/health | python -m json.tool
```

Resposta esperada:

```json
{
  "status": "ok",
  "service": "labia-chat"
}
```

### Health Check do vLLM (se estiver rodando localmente)

```bash
curl -s http://127.0.0.1:8000/health
```

---

## Como Testar vLLM Diretamente

### Com API Key (se configurada)

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${VLLM_API_KEY}" \
  -d '{
    "model": "qwen-coder-next",
    "messages": [{"role": "user", "content": "ping"}],
    "temperature": 0.0,
    "max_tokens": 32
  }' | python -m json.tool
```

### Sem API Key

```bash
curl -s http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-coder-next",
    "messages": [{"role": "user", "content": "ping"}],
    "temperature": 0.0,
    "max_tokens": 32
  }' | python -m json.tool
```

---

## Como Testar `/chat/model/ping`

Endpoint diagnóstico que valida geração mínima via vLLM sem persistir nada.

```bash
curl -sS -X POST http://127.0.0.1:8010/chat/model/ping \
  -H "Authorization: Bearer ${AI_SCOPE_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "ping"}' | python -m json.tool
```

Resposta esperada:

```json
{
  "response": "Pong!"
}
```

---

## Como Criar Conversa

```bash
CONVERSATION_ID=$(
  curl -sS -X POST http://127.0.0.1:8010/chat/conversations \
    -H "Authorization: Bearer ${AI_SCOPE_ACCESS_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{"title": "Smoke test geração persistente"}' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)

echo "$CONVERSATION_ID"
```

---

## Como Chamar Geração Persistente

```bash
curl -sS -X POST "http://127.0.0.1:8010/chat/conversations/${CONVERSATION_ID}/generate" \
  -H "Authorization: Bearer ${AI_SCOPE_ACCESS_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Responda em uma frase curta e completa: o que é uma supernova tipo Ia?"}' \
  | python -m json.tool
```

Resposta esperada:

```json
{
  "id": "uuid-do-mensagem",
  "conversation_id": "uuid-da-conversa",
  "role": "assistant",
  "content": "Uma supernova tipo Ia é uma explosão estelar catastrófica que ocorre em sistemas binários onde uma anã branca acumula matéria de sua estrela companheira...",
  "sequence_index": 1,
  "model": "qwen-coder-next",
  "metadata": {},
  "created_at": "2026-05-28T..."
}
```

---

## Como Listar Conversas (com paginação)

```bash
curl -sS "http://127.0.0.1:8010/chat/conversations?limit=20&offset=0" \
  -H "Authorization: Bearer ${AI_SCOPE_ACCESS_TOKEN}" \
  | python -m json.tool
```

### Parâmetros de paginação

| Parâmetro | Padrão | Mínimo | Máximo | Descrição |
|-----------|--------|--------|--------|-----------|
| `limit`   | 20     | 1      | 100    | Número máximo de conversas a retornar |
| `offset`  | 0      | 0      | -      | Número de conversas a pular |

- Valores inválidos (`limit < 1`, `limit > 100`, `offset < 0`) retornam HTTP 422.
- Conversas são ordenadas do mais recente para o mais antigo.

---

## Como Listar Mensagens (com paginação)

```bash
curl -sS "http://127.0.0.1:8010/chat/conversations/${CONVERSATION_ID}/messages?limit=50&offset=0" \
  -H "Authorization: Bearer ${AI_SCOPE_ACCESS_TOKEN}" \
  | python -m json.tool
```

### Parâmetros de paginação

| Parâmetro | Padrão | Mínimo | Máximo | Descrição |
|-----------|--------|--------|--------|-----------|
| `limit`   | 50     | 1      | 200    | Número máximo de mensagens a retornar |
| `offset`  | 0      | 0      | -      | Número de mensagens a pular |

- Valores inválidos (`limit < 1`, `limit > 200`, `offset < 0`) retornam HTTP 422.
- Mensagens são ordenadas cronologicamente (do mais antigo para o mais recente).

Resposta esperada:

```json
[
  {
    "id": "uuid-mensagem-0",
    "conversation_id": "uuid-da-conversa",
    "role": "user",
    "content": "Responda em uma frase curta e completa: o que é uma supernova tipo Ia?",
    "sequence_index": 0,
    "model": null,
    "metadata": {},
    "created_at": "2026-05-28T..."
  },
  {
    "id": "uuid-mensagem-1",
    "conversation_id": "uuid-da-conversa",
    "role": "assistant",
    "content": "Uma supernova tipo Ia é uma explosão estelar catastrófica...",
    "sequence_index": 1,
    "model": "qwen-coder-next",
    "metadata": {},
    "created_at": "2026-05-28T..."
  }
]
```

---

## Resultado Esperado

Após o fluxo completo de geração persistente:

| Item | Status Esperado |
|------|-----------------|
| Mensagem `user` | `sequence_index=0`, `model=null` |
| Mensagem `assistant` | `sequence_index=1`, `model="qwen-coder-next"` |
| Resposta persistida | Armazenada no banco de dados |
| Conversa associada | Pertence ao usuário autenticado |

---

## Problemas Comuns

### 401 Unauthorized no vLLM

**Sintoma:** Erro `401 Unauthorized` ao chamar o vLLM

**Causa:** Falta `VLLM_API_KEY` ou a chave está incorreta

**Solução:** Configure `VLLM_API_KEY` no arquivo `.env`:

```bash
echo "VLLM_API_KEY=your-api-key-here" >> backend/.env
```

---

### 401 Unauthorized no Backend

**Sintoma:** Erro `401 Unauthorized` ao chamar endpoints protegidos

**Causa:** Falta `Authorization: Bearer <token>` ou token inválido/expirado

**Solução:** Verifique que o token AI-Scope é válido e não expirou:

```bash
echo "Token inválido ou expirado. Obtenha um novo token no AI-Scope."
```

---

### 403 Forbidden - Role Insufficiente

**Sintoma:** Erro `403 Forbidden` com mensagem "User does not have required role"

**Causa:** Usuário não possui a role `chat_vllm`

**Solução:** Solicite ao administrador do AI-Scope que adicione a role `chat_vllm` ao seu usuário.

---

### 502 Bad Gateway

**Sintoma:** Erro `502 Bad Gateway` ao chamar `/generate`

**Causa:** vLLM está indisponível, falha na resposta ou timeout

**Solução:** Verifique se o vLLM está rodando e acessível:

```bash
# Teste direto
curl http://127.0.0.1:8000/v1/models

# Verifique logs do vLLM
# Verifique se a porta 8000 está aberta
```

---

### JSON Vazio ou URL Quebrada

**Sintoma:** Erro ao parsear JSON vazio ou URL inválida

**Causa:** URL do vLLM está incorreta ou servidor não responde

**Solução:** Verifique `VLLM_BASE_URL` no `.env`:

```bash
# Verifique a configuração
grep VLLM_BASE_URL backend/.env

# Teste a conexão
curl -v http://127.0.0.1:8000/v1/models
```

---

### UUID Quebrado em Múltiplas Linhas

**Sintoma:** Erro `422 Unprocessable Entity` ou UUID inválido

**Causa:** Quebra de linha acidental ao copiar UUID no shell

**Solução:** Copie o UUID completo em uma única linha:

```bash
# ERRADO (UUID quebrado):
CONVERSATION_ID="12345678-
abcd-ef00-1234-
567890abcdef"

# CORRETO (UUID em uma linha):
CONVERSATION_ID="12345678-abcd-ef00-1234-567890abcdef"
```

---

## Estrutura de Services

### Services do Backend de Chat

| Service | Responsabilidade |
|---------|------------------|
| `AuthService` | Valida token ADSS e verifica roles |
| `ChatUserSyncService` | Sincroniza usuário ADSS com tabela `chat_users` |
| `ChatPersistenceService` | Gerencia conversas e mensagens no banco |
| `VLLMClient` | Cliente HTTP para comunicação com vLLM |
| `ChatGenerationService` | Gera respostas usando vLLM |
| `ChatCompletionService` | Orquestra persistência + geração |

### Fluxo de Dependências

```
FastAPI Endpoint
    ↓
get_current_chat_user (deps.py)
    ↓
AuthService → AdssClient → ADSS API
    ↓
ChatUserSyncService → ChatUserRepository → PostgreSQL
    ↓
ChatCompletionService
    ↓
├─→ ChatPersistenceService → PostgreSQL
└─→ ChatGenerationService → VLLMClient → vLLM API
```

---

## Endpoints Disponíveis

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/health` | Health check do backend | Não |
| GET | `/auth/me` | Valida token e retorna usuário | Sim |
| GET | `/chat/conversations` | Lista conversas do usuário | Sim |
| POST | `/chat/conversations` | Cria nova conversa | Sim |
| GET | `/chat/conversations/{id}` | Obtém conversa específica | Sim |
| POST | `/chat/conversations/{id}/archive` | Arquiva conversa | Sim |
| POST | `/chat/conversations/{id}/messages` | Cria mensagem manual | Sim |
| GET | `/chat/conversations/{id}/messages` | Lista mensagens | Sim |
| POST | `/chat/model/ping` | Teste de geração (sem persistência) | Sim |
| POST | `/chat/conversations/{id}/generate` | Geração persistente | Sim |

---

## Testes

### Executar testes

```bash
cd backend
python -m pytest tests/ -v
```

### Executar lint

```bash
cd backend
python -m ruff check src/ tests/
```

### Verificar migrations

```bash
cd backend
python -m alembic current

---

## CLI de Chat

O próximo cliente oficial de validação do backend será o CLI de chat.

Objetivo:

- validar o backend como cliente real antes do frontend;
- testar autenticação, criação de conversa, geração persistente e leitura de histórico;
- servir como ferramenta de smoke test operacional.

Documentação do CLI:

- `docs/cli-chat.md`

O CLI deve chamar apenas o backend. Ele não deve chamar o vLLM diretamente.

O histórico de conversas e mensagens deve continuar tendo o backend/PostgreSQL como fonte de verdade. O CLI não deve persistir mensagens localmente.

---

## Validação Operacional (Smoke Test)

Antes de iniciar o desenvolvimento frontend, execute este fluxo manual ou automatizado para validar que o backend e CLI funcionam end-to-end.

### Pré-requisitos

| Componente | Status | Notas |
|------------|--------|-------|
| Backend rodando | Obrigatório | `http://127.0.0.1:8010` (padrão) |
| Token AI-Scope | Obrigatório | Exportar `LABIA_CHAT_TOKEN` |
| Banco PostgreSQL | Obrigatório | Para persistência de conversas/mensagens |
| vLLM | Opcional | Apenas para testes de geração (`--with-model`) |

### Configuração Segura do Token

**NUNCA** exiba ou salve tokens em arquivos de log. Use este método seguro:

```bash
read -rsp "AI-Scope token: " LABIA_CHAT_TOKEN
export LABIA_CHAT_TOKEN
echo
```

Ou, se já tiver um token válido:

```bash
export LABIA_CHAT_TOKEN=seu-token-aqui
```

### Script de Smoke Test Automatizado

O repositório inclui um script de smoke test que valida o fluxo completo:

```bash
# Core smoke (sem vLLM)
bash backend/scripts/smoke_cli.sh

# Full smoke (com geração, requer vLLM)
bash backend/scripts/smoke_cli.sh --with-model

# Com URL customizada
bash backend/scripts/smoke_cli.sh --api-url http://127.0.0.1:8010
```

#### O que o script valida

| Passo | Comando | Obrigatório | O que valida |
|-------|---------|-------------|--------------|
| 1 | `curl /health` | Sim | Backend está rodando |
| 2 | `labia-chat auth me` | Sim | Token válido + usuário ativo |
| 3 | `labia-chat conversations create` | Sim | Criação de conversa |
| 4 | `labia-chat conversations list` | Sim | Listagem com paginação |
| 5 | `labia-chat messages list` | Sim | Listagem de mensagens (vazia) |
| 6 | `labia-chat chat send` | Opcional | Geração via vLLM |
| 7 | `labia-chat messages list` | Opcional | Mensagem persistida |
| 8 | `curl /chat/model/ping` | Opcional | Endpoint de ping direto |

#### Segurança do script

- **NUNCA** exibe o token na saída
- Usa `set -euo pipefail` para falhar em erros
| Requer `LABIA_CHAT_TOKEN` para ser definido
| Usa `read -rsp` para entrada segura de token

### Validação Manual (Checklist)

Se preferir validar manualmente, execute estes passos:

```bash
# 1. Health check
curl -s http://127.0.0.1:8010/health | python -m json.tool

# 2. Validar token
labia-chat auth me

# 3. Criar conversa
labia-chat conversations create --title "Smoke Test"

# 4. Listar conversas
labia-chat conversations list --limit 5 --offset 0

# 5. Listar mensagens (deve estar vazia)
labia-chat messages list <conversation-id> --limit 10 --offset 0

# 6. Enviar mensagem (requer vLLM)
labia-chat chat send <conversation-id> "Smoke test message"

# 7. Listar mensagens (deve ter 1 mensagem)
labia-chat messages list <conversation-id> --limit 10 --offset 0
```

### Sucesso vs Falha

| Resultado | Indicação |
|-----------|-----------|
| **Sucesso** | Todos os passos obrigatórios (1-5) passam |
| **Falha** | Qualquer passo obrigatório falha |
| **Opcional** | Passos 6-8 podem falhar se vLLM não estiver disponível |

### Erros Comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `401 Unauthorized` | Token inválido/expirado | Obtenha novo token no AI-Scope |
| `403 Forbidden` | Sem role `chat_vllm` | Solicite a role ao administrador |
| `502 Bad Gateway` | vLLM indisponível | Inicie o vLLM ou use `--with-model` apenas quando vLLM estiver rodando |
| `connection refused` | Backend não rodando | Inicie o backend em `http://127.0.0.1:8010` |

---

## Testes
