'use client'

// Hook principal de chat para o Chat Lab-IA
import { useState, useCallback, useRef } from 'react'
import { Message, ToolCall } from '@/types'
import { estimateMessagesTokens } from '@/lib/token-estimator'
import { chatStream } from '@/lib/vllm-client'
import { executeTool, availableTools } from '@/lib/tools'

// System prompt padrão
const DEFAULT_SYSTEM_PROMPT =
  'Voce e o assistente de IA do Laboratorio de Inteligencia Artificial do CBPF (Centro Brasileiro de Pesquisas Fisicas). Voce auxilia pesquisadores, estudantes de mestrado, doutorado e pos-doutorado com tarefas de programacao, analise de dados, machine learning e questoes tecnicas gerais. Seja preciso, objetivo e didatico. Quando escrever codigo, prefira solucoes simples, testaveis e bem comentadas. Responda em portugues quando o usuario escrever em portugues.'

// Limite de tokens para o contexto
const MAX_CONTEXT_TOKENS = 55000

// Limite de recursão para chamadas de ferramenta
const MAX_TOOL_CALL_RECURSION = 3

/**
 * Estado para tool calls em execução
 */
interface ToolCallState {
  toolCall: ToolCall
  result: string | null
  isExecuting: boolean
}

/**
 * Hook principal que orquestra todo o estado do chat.
 * Gerencia mensagens, streaming, abortação, estimativa de tokens e tool calling.
 */
export function useChat() {
  // Estado interno
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'system-0',
      role: 'system',
      content: DEFAULT_SYSTEM_PROMPT,
      createdAt: new Date(),
    },
  ])
  const [isStreaming, setIsStreaming] = useState(false)
  const [tokenCount, setTokenCount] = useState(0)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [toolCallState, setToolCallState] = useState<ToolCallState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toolCallRecursionCount, setToolCallRecursionCount] = useState(0)

  // Atualiza o contador de tokens baseado nas mensagens atuais
  const updateTokenCount = useCallback((currentMessages: Message[]) => {
    setTokenCount(estimateMessagesTokens(currentMessages))
  }, [])

  // Envia uma mensagem do usuário e processa a resposta do modelo
  const sendMessage = useCallback(
    async (
      userInput: string,
      tools?: object[],
      baseMessages?: Message[]
    ): Promise<void> => {
      const currentMessages = baseMessages || messages

      // Cria mensagem do usuário
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: userInput,
        createdAt: new Date(),
      }

      // Trunca o contexto antes de enviar (inclui a nova mensagem do usuário)
      const messagesWithUser = [...currentMessages, userMessage]
      const trimmedMessages = messagesWithUser.slice(0, 1).concat(
        messagesWithUser
          .slice(1)
          .filter((m) => m.role !== 'system')
          .slice(-8)
      )

      // Verifica se precisa truncar por tokens
      const messagesToSend =
        estimateMessagesTokens(trimmedMessages) > MAX_CONTEXT_TOKENS
          ? trimmedMessages
          : messagesWithUser

      // Cria mensagem vazia do assistant para ir preenchendo
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: '',
        createdAt: new Date(),
      }

      // Adiciona mensagem do usuário e mensagem do assistant ao histórico
      setMessages([...currentMessages, userMessage, assistantMessage])
      setIsStreaming(true)

      // Cria novo AbortController para esta requisição
      const abortController = new AbortController()
      abortControllerRef.current = abortController

      let fullContent = ''
      let currentToolCall: ToolCall | null = null

      try {
        await chatStream(
          messagesToSend,
          tools,
          (token: string) => {
            // Atualiza o conteúdo da mensagem do assistant
            fullContent += token
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessage.id
                  ? { ...msg, content: fullContent }
                  : msg
              )
            )
          },
          (toolCall: ToolCall) => {
            // Armazena o tool_call na mensagem do assistant
            currentToolCall = toolCall
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantMessage.id
                  ? {
                      ...msg,
                      tool_calls: msg.tool_calls
                        ? [...msg.tool_calls, toolCall]
                        : [toolCall],
                    }
                  : msg
              )
            )
          },
          abortController.signal
        )

        // Verifica se houve tool calls na resposta
        // Usa o estado atualizado para encontrar a mensagem do assistant
        const updatedMessages = [...messages, userMessage, assistantMessage]
        const assistantMsg = updatedMessages.find((m) => m.id === assistantMessage.id)
        if (assistantMsg?.tool_calls && assistantMsg.tool_calls.length > 0) {
          // Processa as tool calls e aguarda a conclusão
          void processToolCalls(assistantMsg.tool_calls, assistantMessage.id)
        }

        // Atualiza token count após a resposta completa
        setMessages((prev) => {
          const updated = [...prev]
          updateTokenCount(updated)
          return updated
        })
      } catch (error) {
        const errorContent =
          error instanceof Error
            ? `**Erro:** ${error.message}`
            : 'Ocorreu um erro desconhecido ao processar sua solicitação.'

        setMessages((prev) => {
          const updated = prev.map((msg) =>
            msg.id === assistantMessage.id
              ? { ...msg, content: errorContent }
              : msg
          )
          updateTokenCount(updated)
          return updated
        })
        setError(error instanceof Error ? error.message : 'Erro desconhecido')
      } finally {
        setIsStreaming(false)
        abortControllerRef.current = null
      }
    },
    [messages, updateTokenCount]
  )

  // Processa as tool calls e continua a conversa
  const processToolCalls = useCallback(
    async (
      toolCalls: ToolCall[],
      assistantMessageId: string
    ): Promise<void> => {
      // Verifica se atingiu o limite de recursão
      if (toolCallRecursionCount >= MAX_TOOL_CALL_RECURSION) {
        const limitMessage: Message = {
          id: `limit-${Date.now()}`,
          role: 'assistant',
          content:
            'Limite de chamadas de ferramentas atingido neste turno.',
          createdAt: new Date(),
        }
        setMessages((prev) => [...prev, limitMessage])
        return
      }

      // Processa cada tool call
      for (const toolCall of toolCalls) {
        // Define o estado de execução
        setToolCallState({
          toolCall,
          result: null,
          isExecuting: true,
        })

        try {
          // Executa a ferramenta
          const result = await executeTool(
            toolCall.function.name,
            toolCall.function.arguments
          )

          // Atualiza o estado com o resultado
          setToolCallState({
            toolCall,
            result,
            isExecuting: false,
          })

          // Adiciona a mensagem do tool ao histórico
          const toolMessage: Message = {
            id: `tool-${Date.now()}-${toolCall.id}`,
            role: 'tool',
            tool_call_id: toolCall.id,
            content: result,
            createdAt: new Date(),
          }

          setMessages((prev) => [...prev, toolMessage])

          // Faz nova chamada ao modelo com o resultado da ferramenta
          // Trunca o contexto para evitar overflow (inclui a mensagem do tool)
          const messagesWithTool = [...messages, toolMessage]
          const trimmedMessages = messagesWithTool.slice(0, 1).concat(
            messagesWithTool
              .slice(1)
              .filter((m) => m.role !== 'system')
              .slice(-8)
          )

          // Cria nova mensagem do assistant para a resposta do modelo
          const newAssistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: '',
            createdAt: new Date(),
          }

          setMessages((prev) => [...prev, newAssistantMessage])
          setIsStreaming(true)

          const newAbortController = new AbortController()
          abortControllerRef.current = newAbortController

          let fullContent = ''

          try {
            await chatStream(
              trimmedMessages,
              availableTools,
              (token: string) => {
                fullContent += token
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === newAssistantMessage.id
                      ? { ...msg, content: fullContent }
                      : msg
                  )
                )
              },
              (toolCall: ToolCall) => {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === newAssistantMessage.id
                      ? {
                          ...msg,
                          tool_calls: msg.tool_calls
                            ? [...msg.tool_calls, toolCall]
                            : [toolCall],
                        }
                      : msg
                  )
                )
              },
              newAbortController.signal
            )

            // Atualiza contador de recursão
            setToolCallRecursionCount((prev) => prev + 1)

            // Verifica se houve mais tool calls
            // Usa o estado atualizado para encontrar a mensagem do assistant
            setMessages((prev) => {
              const newAssistantMsg = prev.find(
                (m) => m.id === newAssistantMessage.id
              )
              if (
                newAssistantMsg?.tool_calls &&
                newAssistantMsg.tool_calls.length > 0
              ) {
                void processToolCalls(
                  newAssistantMsg.tool_calls,
                  newAssistantMessage.id
                )
              }
              return prev
            })
          } catch (error) {
            const errorContent =
              error instanceof Error
                ? `**Erro:** ${error.message}`
                : 'Ocorreu um erro desconhecido ao processar sua solicitação.'

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === newAssistantMessage.id
                  ? { ...msg, content: errorContent }
                  : msg
              )
            )
            setError(
              error instanceof Error ? error.message : 'Erro desconhecido'
            )
          } finally {
            setIsStreaming(false)
            abortControllerRef.current = null
          }
        } catch (error) {
          // Em caso de erro na execução da ferramenta
          const errorMsg: Message = {
            id: `tool-error-${Date.now()}-${toolCall.id}`,
            role: 'tool',
            tool_call_id: toolCall.id,
            content: `Erro ao executar ferramenta: ${error instanceof Error ? error.message : String(error)}`,
            createdAt: new Date(),
          }
          setMessages((prev) => [...prev, errorMsg])
        }
      }

      // Limpa o estado de tool call após processar todos
      setToolCallState(null)
    },
    [messages, toolCallRecursionCount]
  )

  // Para a geração atual
  const stopGeneration = useCallback((): void => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
  }, [])

  // Limpa o histórico, preservando apenas o system prompt
  const clearHistory = useCallback((): void => {
    setMessages((prev) => {
      const systemMessage = prev.find((m) => m.role === 'system')
      return systemMessage ? [systemMessage] : []
    })
    setTokenCount(0)
    setToolCallRecursionCount(0)
    setError(null)
  }, [])

  // Define ou substitui o system prompt
  const setSystemPrompt = useCallback((prompt: string): void => {
    setMessages((prev) => {
      const newMessages = [...prev]
      const systemIndex = newMessages.findIndex((m) => m.role === 'system')

      if (systemIndex >= 0) {
        newMessages[systemIndex] = {
          ...newMessages[systemIndex],
          content: prompt,
        }
      } else {
        newMessages.unshift({
          id: `system-${Date.now()}`,
          role: 'system',
          content: prompt,
          createdAt: new Date(),
        })
      }

      updateTokenCount(newMessages)
      return newMessages
    })
  }, [updateTokenCount])

  // Carrega mensagens de uma sessão no useChat
  const loadMessages = useCallback((newMessages: Message[]): void => {
    setMessages(newMessages)
    updateTokenCount(newMessages)
    setToolCallRecursionCount(0)
    setError(null)
  }, [updateTokenCount])

  return {
    messages,
    isStreaming,
    tokenCount,
    sendMessage,
    stopGeneration,
    clearHistory,
    setSystemPrompt,
    loadMessages,
    toolCallState,
    error,
  }
}
