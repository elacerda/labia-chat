# Plano de Implementação - Etapa 1: Fundação do Projeto

## Arquivos a Criar

### 1. package.json
- Dependências: next, react, react-dom, typescript, tailwindcss, @types/react, @types/node
- Dependências de features: react-markdown, remark-gfm, react-syntax-highlighter, @types/react-syntax-highlighter
- Scripts: dev, build, start, lint

### 2. .env.example
- VLLM_BASE_URL=http://152.84.203.222:8000/v1
- VLLM_API_KEY=labia-local-key
- VLLM_MODEL_ID=qwen-coder-next
- Comentário sobre não usar NEXT_PUBLIC_ para API key

### 3. tsconfig.json
- strict: true
- esModuleInterop, skipLibCheck, forceConsistentCasingInFileNames
- paths configurado para @/* -> ./src/*

### 4. postcss.config.js
- plugins: tailwindcss, autoprefixer

### 5. tailwind.config.js
- content: ["./app/**/*.{js,ts,jsx,tsx}"]
- theme: extend colors (slate-900, slate-100)
- plugins: []

### 6. /types/index.ts
- Role: "user" | "assistant" | "system" | "tool"
- ToolCall: { id, type, function: { name, arguments } }
- Message: { id, role, content, tool_calls?, tool_call_id?, createdAt }
- ConversationSession: { id, title, messages, createdAt, updatedAt }
- ServerStatus: "online" | "slow" | "offline" | "unknown"
- ChatRequestPayload: todos os campos da API

### 7. /lib/token-estimator.ts
- estimateTokens(text): number (text.length / 4)
- estimateMessagesTokens(messages): number (soma + 4 por mensagem)
- shouldTrimContext(messages, limitTokens): boolean
- trimContext(messages, limitTokens, keepLastN): Message[] (preserva system prompt)

### 8. /lib/vllm-client.ts
- buildPayload(messages, tools?): ChatRequestPayload
- chatStream(...): Promise<void> (streaming com SSE)
- checkHealth(): Promise<{ status, latencyMs }> (GET /health)

### 9. /app/layout.tsx
- Root layout com html, body, metadados
- Import globals.css

### 10. /app/globals.css
- @tailwind base/components/utilities
- background: #0f172a
- color: #f1f5f9

### 11. /app/chat/page.tsx
- Placeholder com texto "Chat Lab-IA - em construcao"

## Ordem de Criação
1. package.json
2. .env.example
3. tsconfig.json
4. postcss.config.js
5. tailwind.config.js
6. /types/index.ts
7. /lib/token-estimator.ts
8. /lib/vllm-client.ts
9. /app/layout.tsx
10. /app/globals.css
11. /app/chat/page.tsx
