# Prompts para agentes/modelos — Implementação de streaming SSE

Data: 2026-05-28  
Idioma dos prompts: inglês, conforme preferência do projeto.

## 1. Prompt para Cline/Qwen — modo Plan

Use este prompt primeiro, em **Cline/Qwen modo Plan**.

```text
We are working on the labia-chat repository.

Goal:
Implement ChatGPT-style streaming responses using Server-Sent Events while preserving the existing non-streaming backend contract.

Important context:
- The backend REST contract was frozen after MVP 2.16.
- This task is an explicit contract extension requested for frontend streaming.
- Do not modify or break the existing endpoint:
  POST /chat/conversations/{conversation_id}/generate
- Add a new endpoint instead:
  POST /chat/conversations/{conversation_id}/generate/stream
- Do not modify frontend files in this task.
- Do not change database models or migrations unless absolutely necessary.
- Do not print secrets or full diffs.

Reference behavior:
- Use FastAPI StreamingResponse.
- Return media_type="text/event-stream".
- Use headers:
  Cache-Control: no-cache
  Connection: keep-alive
  X-Accel-Buffering: no

Streaming protocol:
- Normal assistant chunks must be plain SSE data messages, not JSON:
  data: text chunk
- Do NOT stream repeated objects like:
  data: {"token": "..."}
- Use structured named events only for control:
  event: done
  data: {"message_id":"..."}

  event: error
  data: {"detail":"Falha ao gerar resposta"}

Newline preservation:
- The SSE text helper must preserve chunks such as "\n", "\n\n", trailing newlines, indentation, tabs, and Markdown code fences.
- Do not use a naive splitlines() implementation that drops trailing/empty lines.
- Prefer a helper equivalent to:
  if text == "":
      return ""
  safe_text = text.replace("\n", "\ndata: ")
  return f"data: {safe_text}\n\n"

Persistence semantics:
1. Persist the user message before model generation starts.
2. Stream deltas from the vLLM OpenAI-compatible endpoint using stream=true.
3. Accumulate assistant text during streaming.
4. Persist the assistant message only after the stream completes successfully.
5. If the client disconnects or the model stream fails before completion, do not persist a partial assistant response.
6. Do not hold a database transaction open during the whole streaming process.

Please inspect the current code and produce a concise implementation plan:
- files to change
- new helpers/functions/classes
- endpoint contract
- tests to add/update
- risks and mitigations
- validation commands

Do not implement yet.
```

## 2. Prompt para Cline/Qwen — modo Act

Use este prompt apenas depois de revisar o plano. Modo: **Act**.

```text
Implement the approved SSE streaming plan for labia-chat.

Constraints:
- Preserve the existing non-streaming endpoint:
  POST /chat/conversations/{conversation_id}/generate
- Add:
  POST /chat/conversations/{conversation_id}/generate/stream
- Do not modify frontend files.
- Do not alter existing REST response shapes, pagination, auth semantics, database models, or migrations.
- Keep changes small and focused.
- Do not print full diffs.
- Never expose tokens, VLLM_API_KEY, DATABASE_URL, or stack traces in user-facing errors.

Required behavior:
1. Add tested SSE helpers:
   - plain text chunks as `data: ...\n\n`;
   - named JSON events for `done` and `error`;
   - preserve newlines and whitespace-only chunks.
2. Add vLLM streaming support using OpenAI-compatible `stream=true`.
3. Add service-level streaming generation/completion.
4. Persist user message before streaming.
5. Persist assistant message only after successful completion.
6. Do not persist partial assistant messages on generation error or client disconnect.
7. Add FastAPI StreamingResponse endpoint with media_type="text/event-stream" and anti-buffering headers.
8. Add/adjust tests for helpers, vLLM stream parsing, service persistence behavior, streaming endpoint, and non-streaming regression.

Validation:
- cd backend
- python -m ruff check src/ tests/
- python -m pytest tests/ -q
- python -m alembic current
- cd ..
- git diff --check
- git diff --stat
- git status --short

Return only:
- files changed
- concise summary
- validation results
- any known limitations
```

## 3. Prompt para Codex CLI

```text
You are modifying the labia-chat repository on branch feature/chat-streaming.

Implement SSE chat streaming as an additive backend contract extension.

Read these docs first:
- docs/streaming/README.md
- docs/streaming/api-contract.md
- docs/streaming/implementation-guide.md
- docs/streaming/testing-validation.md
- docs/adr/0002-add-sse-chat-streaming-endpoint.md

Then implement according to the documented contract.

Do not change frontend files.
Do not break existing /generate.
Do not change DB models or migrations unless the code inspection proves it is unavoidable.
Do not persist partial assistant responses.
Do not expose secrets.

Run:
cd backend
python -m ruff check src/ tests/
python -m pytest tests/ -q
python -m alembic current
cd ..
git diff --check
git diff --stat
git status --short

Summarize results without printing full diffs.
```

## 4. Prompt para revisão por outra IA

```text
Review the proposed SSE streaming implementation plan for labia-chat.

Focus on:
- whether the endpoint is additive and preserves the existing /generate contract;
- whether SSE plain text chunks are correctly encoded;
- whether newline-only chunks are preserved;
- whether the persistence semantics avoid partial assistant messages;
- whether DB transactions are not held open during streaming;
- whether vLLM stream=true parsing is robust;
- whether frontend consumption via fetch ReadableStream is compatible;
- whether tests cover the important edge cases;
- whether any security/secrets risks remain.

Return:
- blockers
- recommended changes
- optional improvements
- final go/no-go
```
