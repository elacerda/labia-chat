# Chat Lab-IA / SCoPE-AI

Interface de conversação com o modelo Qwen3-Coder-Next, desenvolvida para uso interno no Laboratório Lab-IA / CBPF.

## Instalação

Pré-requisitos:

- Node.js 22
- npm

1. Clone o repositório:
   ```bash
   git clone <url-do-repositorio>
   cd labia-chat
   ```

2. Instale as dependências:
   ```bash
   npm install
   ```

3. Opcionalmente, crie um arquivo `.env.local` para sobrescrever os padrões de conexão com o vLLM:
   ```bash
   touch .env.local
   ```

4. Preencha as variáveis de ambiente necessárias no arquivo `.env.local` (veja a seção abaixo).

5. Inicie o servidor de desenvolvimento:
   ```bash
   npm run dev
   ```

6. Acesse `http://localhost:3000/chat` no seu navegador.

## Variáveis de ambiente

| Variável | Descrição | Valor padrão |
|----------|-----------|--------------|
| `VLLM_BASE_URL` | URL base OpenAI-compatible do servidor vLLM (ex: `http://localhost:8000/v1`) | `<YOUR_SERVER_HTTP>` |
| `VLLM_API_KEY` | API key para autenticação no servidor vLLM | `<YOUR_API_KEY>` |
| `VLLM_MODEL_ID` | ID do modelo carregado no servidor vLLM | `qwen-coder-next` |

## Arquitetura resumida

A aplicação é construída com **Next.js 14** (App Router) e **React 18**, utilizando **TypeScript** para tipagem estática. O design segue um padrão escuro, seco e científico, alinhado à identidade visual do SCoPE-AI.

### Módulos principais

- **`/app`**: Estrutura de páginas Next.js. O arquivo [`app/chat/page.tsx`](app/chat/page.tsx) é o ponto de entrada principal, orquestrando o layout completo com sidebar, header, área de chat e barra de input.
  - [`app/api/health/route.ts`](app/api/health/route.ts): Rota server-side que consulta o health check do vLLM sem expor esse detalhe diretamente ao navegador.

- **`/components`**: Componentes React reutilizáveis:
  - [`ChatWindow`](components/ChatWindow.tsx): Exibe o histórico de mensagens com scroll automático e tela de boas-vindas
  - [`MessageBubble`](components/MessageBubble.tsx): Renderiza cada mensagem individual com suporte a markdown, blocos de código e botão de cópia
  - [`InputBar`](components/InputBar.tsx): Área de input com textarea expansível, botões de enviar/parar e contador de tokens
  - [`SidebarHistory`](components/SidebarHistory.tsx): Lista de conversas anteriores com criação, exclusão individual e limpeza completa
  - [`StatusBadge`](components/StatusBadge.tsx): Indicador visual do status do servidor vLLM
  - [`SystemPromptEditor`](components/SystemPromptEditor.tsx): Modal para editar o system prompt
  - [`ToolCallDisplay`](components/ToolCallDisplay.tsx): Exibe o status de execução de ferramentas

- **`/hooks`**: Custom hooks para lógica de estado:
  - [`useChat`](hooks/useChat.ts): Gerencia o estado do chat (mensagens, streaming, tool calling)
  - [`useConversations`](hooks/useConversations.ts): Gerencia o histórico de sessões (criar, carregar, salvar, deletar)
  - [`useServerStatus`](hooks/useServerStatus.ts): Verifica periodicamente o status do servidor vLLM

- **`/lib`**: Lógica de negócio:
  - [`vllm-client.ts`](lib/vllm-client.ts): Cliente HTTP para comunicação com o servidor vLLM
  - [`conversation.ts`](lib/conversation.ts): Interface `ConversationStore` para persistência de conversas
  - [`tools.ts`](lib/tools.ts): Definição das ferramentas disponíveis para o modelo
  - [`token-estimator.ts`](lib/token-estimator.ts): Estimativa de contagem de tokens

- **`/types`**: Tipos TypeScript compartilhados ([`types/index.ts`](types/index.ts))

### Fluxo de dados

1. O usuário digita uma mensagem no [`InputBar`](components/InputBar.tsx) e clica em "Enviar"
2. A página [`app/chat/page.tsx`](app/chat/page.tsx) garante que a mensagem seja associada à sessão ativa correta. Sessões novas começam com o título `Nova conversa` e só são renomeadas a partir do primeiro prompt enviado naquela própria sessão.
3. O hook [`useChat`](hooks/useChat.ts) chama [`sendMessage()`](hooks/useChat.ts), que:
   - Adiciona a mensagem do usuário ao estado local
   - Chama o [`vllm-client`](lib/vllm-client.ts) para enviar a requisição ao servidor
   - Recebe a resposta em streaming e atualiza o estado
   - Em caso de erro no streaming, preenche a resposta do assistant com a mensagem de erro em vez de deixar uma bolha vazia
4. O [`ChatWindow`](components/ChatWindow.tsx) renderiza as mensagens através do [`MessageBubble`](components/MessageBubble.tsx)
5. O [`useConversations`](hooks/useConversations.ts) salva automaticamente cada sessão após cada interação
6. O [`StatusBadge`](components/StatusBadge.tsx) verifica o servidor periodicamente através de `/api/health`

### Persistência de conversas

O sistema usa o `localStorage` do navegador para persistir as conversas. A interface [`ConversationStore`](lib/conversation.ts) permite trocar o adapter de persistência (ex: para uma API REST do SCoPE-AI) com alterações concentradas no módulo de conversas.

Cada sessão salva `createdAt`, `updatedAt`, `title` e a lista de mensagens. Ao recarregar o histórico, as datas serializadas no `localStorage` são convertidas de volta para `Date`, e as sessões são ordenadas por atualização mais recente. O botão **Limpar todas as conversas** remove a chave `labia-chat-sessions` do `localStorage` e recarrega a aplicação.

## Integração com SCoPE-AI

Para integrar com o SCoPE-AI (https://ai-scope.cbpf.br), crie uma implementação de [`ConversationStore`](lib/conversation.ts) e substitua a exportação `conversationStore` no módulo de conversas.

### Passo 1: Criar um adapter de API

Crie um novo arquivo `lib/scope-adapter.ts` implementando a interface `ConversationStore`:

```typescript
// lib/scope-adapter.ts
import type { ConversationSession } from '@/types'
import type { ConversationStore } from './conversation'

export class ScopeApiAdapter implements ConversationStore {
  private baseUrl = 'https://ai-scope.cbpf.br/api'
  private token: string

  constructor(token: string) {
    this.token = token
  }

  private async request(path: string, options?: RequestInit) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...(options?.headers ?? {}),
      },
    })
    if (!res.ok) throw new Error('API error')
    return res.json()
  }

  async list(): Promise<ConversationSession[]> {
    return this.request('/conversations')
  }

  async get(id: string): Promise<ConversationSession | null> {
    return this.request(`/conversations/${id}`)
  }

  async save(session: ConversationSession): Promise<void> {
    await this.request(`/conversations/${session.id}`, {
      method: 'PUT',
      body: JSON.stringify(session),
    })
  }

  async delete(id: string): Promise<void> {
    await this.request(`/conversations/${id}`, { method: 'DELETE' })
  }
}
```

### Passo 2: Atualizar o [`lib/conversation.ts`](lib/conversation.ts)

Substitua a instância local por uma instância do adapter de API:

```typescript
// lib/conversation.ts
import { ScopeApiAdapter } from '@/lib/scope-adapter'

const token = 'SEU_TOKEN_JWT_AQUI'

export const conversationStore: ConversationStore = new ScopeApiAdapter(token)
```

> **Nota**: O projeto ainda não possui um provider de conversas. Hoje a fonte de persistência é controlada pela exportação `conversationStore`.

## Limitações conhecidas

- **Contexto máximo**: 65.536 tokens (configuração do servidor vLLM)
- **Usuários simultâneos**: Máximo de 12 usuários (configuração do servidor)
- **Multimodal**: O modelo não aceita imagens ou arquivos (não é multimodal)
- **Segurança**: A API key do chat não deve ser exposta em produção sem um proxy de backend. O health check já passa por uma rota server-side (`/api/health`), mas o streaming de chat ainda é feito pelo cliente atual.

## Contato

**Eduardo Alberto Duarte Lacerda**  
Email: [dhubax@gmail.com](mailto:dhubax@gmail.com)

---

© 2024 Laboratório Lab-IA / CBPF — Uso interno
