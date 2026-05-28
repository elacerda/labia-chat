# 06 — Política de Mudanças Após Backend Freeze

## Regra geral

Não alterar backend congelado sem uma justificativa explícita.

Mudanças aceitáveis:

- correção de bug real;
- documentação;
- teste que protege contrato existente;
- ajuste operacional de smoke/runbook;
- mudança explicitamente aprovada como nova MVP.

Mudanças que exigem nova decisão:

- alterar formato de resposta REST;
- adicionar wrapper/metadata em endpoints existentes;
- trocar paginação `limit/offset` por cursor;
- mudar autenticação;
- salvar token no CLI;
- adicionar dependências;
- alterar schema de banco;
- modificar fluxo de geração;
- adicionar streaming/websocket;
- introduzir frontend.

## Checklist antes de qualquer alteração

Responder antes de modificar:

```text
1. Qual problema real estamos resolvendo?
2. Isso altera contrato público?
3. Que arquivo de documentação será atualizado?
4. Que teste cobre o comportamento?
5. O smoke core continuará passando?
6. O smoke --with-model continuará passando, se vLLM estiver disponível?
7. Há risco de vazamento de segredo?
```

## Validação mínima obrigatória

```bash
cd backend
python -m ruff check src/ tests/
python -m pytest tests/ -q
python -m alembic current
cd ..

git diff --check
git diff --stat
git status --short
```

## Validação operacional recomendada

```bash
bash backend/scripts/smoke_cli.sh
bash backend/scripts/smoke_cli.sh --with-model
```

O smoke `--with-model` pode depender de infraestrutura local de vLLM.
