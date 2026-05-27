// Tipos TypeScript para o Chat Lab-IA

// Tipos de papéis nas mensagens
export type Role = 'user' | 'assistant' | 'system' | 'tool'

// Representa uma chamada de ferramenta (tool call)
export interface ToolCall {
  id: string
  type: 'function'
  function: {
    name: string
    arguments: string
  }
}

// Representa uma mensagem no chat
export interface Message {
  id: string
  role: Role
  content: string
  tool_calls?: ToolCall[]
  tool_call_id?: string // presente apenas quando role === 'tool'
  createdAt: Date
}

// Representa uma sessão de conversa
export interface ConversationSession {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
}

// Status do servidor vLLM
export type ServerStatus = 'online' | 'slow' | 'offline' | 'unknown'

// Payload da requisição para a API vLLM
export interface ChatRequestPayload {
  model: string
  messages: Array<{
    role: Role
    content: string
    tool_call_id?: string
    tool_calls?: ToolCall[]
  }>
  temperature: number
  top_p: number
  max_tokens: number
  stream: boolean
  tools?: object[]
}
