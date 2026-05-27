# 04 — Modelos, vLLM e desenho model-agnostic

## Objetivo

O backend deve nascer preparado para múltiplos modelos, mesmo que o MVP use apenas um modelo.

O frontend futuro deve conseguir consultar quais modelos estão disponíveis e escolher um `model_id` ao enviar mensagens.

## Provider inicial

Provider inicial:

```text
openai_compatible
```

Implementação inicial:

```text
vLLM /chat/completions
```

## Configuração inicial via `.env`

```env
DEFAULT_MODEL_ID=qwen-coder-next

VLLM_BASE_URL=http://localhost:8000/v1
VLLM_API_KEY=labia-local-key
VLLM_MODEL_NAME=qwen-coder-next
VLLM_CONTEXT_WINDOW=65536
VLLM_DEFAULT_MAX_TOKENS=2048
VLLM_DEFAULT_TEMPERATURE=0.2
```

## Model registry conceitual

No MVP, pode ser implementado em memória a partir do `.env`.

Modelo conceitual:

```json
{
  "id": "qwen-coder-next",
  "display_name": "Qwen3-Coder-Next FP8",
  "provider": "openai_compatible",
  "base_url": "http://localhost:8000/v1",
  "model_name": "qwen-coder-next",
  "context_window": 65536,
  "default_max_tokens": 2048,
  "default_temperature": 0.2,
  "supports_streaming": true,
  "supports_tools": false,
  "supports_vision": false,
  "enabled": true
}
```

## Endpoint de modelos

```http
GET /models
```

Resposta:

```json
{
  "models": [
    {
      "id": "qwen-coder-next",
      "display_name": "Qwen3-Coder-Next FP8",
      "provider": "openai_compatible",
      "context_window": 65536,
      "supports_streaming": true,
      "supports_tools": false,
      "supports_vision": false
    }
  ]
}
```

## Chat com modelo selecionado

Request conceitual:

```json
{
  "conversation_id": "opcional",
  "model_id": "qwen-coder-next",
  "message": "Explique transformers",
  "temperature": 0.2,
  "max_tokens": 2048
}
```

O backend deve resolver `model_id` para configuração interna do provider.

## Futuro

Futuras extensões possíveis:

- múltiplos vLLMs;
- OpenAI externo;
- Ollama;
- modelos multimodais;
- modelos com tool calling;
- modelos por role/grupo;
- modelos habilitados/desabilitados dinamicamente via banco.
