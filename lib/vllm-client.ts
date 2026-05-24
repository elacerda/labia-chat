// Cliente da API vLLM para o Chat Lab-IA
import { Message, ToolCall, ChatRequestPayload, ServerStatus } from '@/types'

// Parâmetros fixos para todas as requisições
const FIXED_PARAMS = {
  model: 'server-configured-model',
  temperature: 1.0,
  top_p: 0.95,
  max_tokens: 2048,
  stream: true,
}

/**
 * Monta o payload da requisição com os parâmetros fixos.
 * 
 * @param messages - Array de mensagens do tipo Message
 * @param tools - Array de objetos representando as ferramentas disponíveis (opcional)
 * @returns Objeto ChatRequestPayload pronto para enviar à API
 */
export function buildPayload(
  messages: Message[],
  tools?: object[]
): ChatRequestPayload {
  // Converte Message[] para o formato simples da API (sem campos extras como id e createdAt)
  const apiMessages = messages.map(({ role, content, tool_calls, tool_call_id }) => ({
    role,
    content,
    tool_call_id,
    tool_calls,
  }))

  return {
    ...FIXED_PARAMS,
    messages: apiMessages,
    tools: tools,
  }
}

/**
 * Envia uma requisição de chat com streaming para a API vLLM.
 * 
 * @param messages - Array de mensagens do tipo Message
 * @param tools - Array de objetos representando as ferramentas disponíveis (opcional)
 * @param onToken - Função callback chamada para cada token recebido no streaming
 * @param onToolCall - Função callback chamada quando uma chamada de ferramenta é recebida
 * @param signal - AbortSignal para cancelar a requisição
 * @returns Promise<void> que resolve quando o streaming termina
 */
export async function chatStream(
  messages: Message[],
  tools: object[] | undefined,
  onToken: (token: string) => void,
  onToolCall: (toolCall: ToolCall) => void,
  signal: AbortSignal
): Promise<void> {
  const payload = buildPayload(messages, tools)

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    })

    // Tratamento de erro HTTP
    if (!response.ok) {
      if (response.status === 429) {
        throw new Error(
          'Servidor ocupado: limite de sessões simultâneas atingido. Tente novamente em alguns instantes.'
        )
      }
      const errorText = await response.text()
      throw new Error(`Erro HTTP ${response.status}: ${errorText}`)
    }

    // Processa o stream Server-Sent Events
    if (!response.body) {
      throw new Error('Resposta não possui body para streaming')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    let buffer = ''
    let accumulatedToolCalls: { [key: string]: ToolCall } = {}

    while (true) {
      const { value, done } = await reader.read()
      
      if (done) break
      if (signal.aborted) {
        // Encerra silenciosamente se abortado
        return
      }

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.trim() === '') continue

        // Ignora linhas de comentário ou sem dados
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6) // Remove "data: "
        
        // Ignora linha de finalização
        if (data.trim() === '[DONE]') continue

        try {
          const chunk = JSON.parse(data)

          // Processa choices se existirem
          if (chunk.choices && chunk.choices.length > 0) {
            const choice = chunk.choices[0]

            // Se houver conteúdo de texto, chama onToken
            if (choice.delta.content) {
              onToken(choice.delta.content)
            }

            // Se houver chamadas de ferramenta, processa
            if (choice.delta.tool_calls) {
              for (const toolCall of choice.delta.tool_calls) {
                // Acumula as chamadas de ferramenta
                if (toolCall.id) {
                  // Nova chamada de ferramenta
                  accumulatedToolCalls[toolCall.id] = {
                    id: toolCall.id,
                    type: 'function',
                    function: {
                      name: toolCall.function?.name || '',
                      arguments: toolCall.function?.arguments || '',
                    },
                  }
                } else {
                  // Atualiza chamada existente
                  const existing = accumulatedToolCalls[toolCall.id]
                  if (existing) {
                    if (toolCall.function?.name) {
                      existing.function.name = toolCall.function.name
                    }
                    if (toolCall.function?.arguments) {
                      existing.function.arguments += toolCall.function.arguments
                    }
                  }
                }
              }

              // Emite todas as chamadas de ferramenta acumuladas
              for (const id in accumulatedToolCalls) {
                onToolCall(accumulatedToolCalls[id])
              }
            }
          }
        } catch (e) {
          // Ignora linhas inválidas
          continue
        }
      }
    }
  } catch (error) {
    // Re-lança erros que não sejam abortados silenciosamente
    if (signal.aborted) {
      return
    }
    throw error
  }
}

/**
 * Verifica a saúde do servidor vLLM.
 * 
 * @returns Objeto com status e latência em ms
 */
export async function checkHealth(): Promise<{ status: ServerStatus; latencyMs: number }> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 8000)

  const startTime = Date.now()

  try {
    const response = await fetch('/api/health', {
      method: 'GET',
      signal: controller.signal,
    })

    const latencyMs = Date.now() - startTime

    clearTimeout(timeoutId)

    if (response.ok) {
      const data = await response.json()
      return {
        status: data.status,
        latencyMs: data.latencyMs,
      }
    } else {
      return { status: 'offline', latencyMs }
    }
  } catch (error) {
    clearTimeout(timeoutId)
    return { status: 'offline', latencyMs: Date.now() - startTime }
  }
}
