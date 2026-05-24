// Hook para gerenciar a lista de sessões de conversa e a sessão ativa

import { useState, useEffect, useCallback } from 'react'
import { ConversationSession, Message } from '@/types'
import { conversationStore, generateSessionId } from '@/lib/conversation'

// System prompt padrão
const DEFAULT_SYSTEM_PROMPT =
  'Voce e o assistente de IA do Laboratorio de Inteligencia Artificial do CBPF (Centro Brasileiro de Pesquisas Fisicas). Voce auxilia pesquisadores, estudantes de mestrado, doutorado e pos-doutorado com tarefas de programacao, analise de dados, machine learning e questoes tecnicas gerais. Seja preciso, objetivo e didatico. Quando escrever codigo, prefira solucoes simples, testaveis e bem comentadas. Responda em portugues quando o usuario escrever em portugues.'

/**
 * Hook que gerencia a lista de sessões e a sessão ativa.
 * Usa o conversationStore para persistência.
 */
export function useConversations() {
  const [sessions, setSessions] = useState<ConversationSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [hasLoadedSessions, setHasLoadedSessions] = useState(false)

  /**
   * Carrega todas as sessões do conversationStore
   */
  const loadSessions = useCallback(async (): Promise<void> => {
    const loadedSessions = await conversationStore.list()
    setSessions(loadedSessions)
    setHasLoadedSessions(true)
  }, [])

  /**
   * Cria uma nova sessão vazia com o system prompt padrão,
   * salva no store e define como ativa.
   */
  const createSession = useCallback(async (): Promise<ConversationSession> => {
    const newSession: ConversationSession = {
      id: generateSessionId(),
      title: 'Nova conversa',
      messages: [
        {
          id: `system-${Date.now()}`,
          role: 'system',
          content: DEFAULT_SYSTEM_PROMPT,
          createdAt: new Date(),
        },
      ],
      createdAt: new Date(),
      updatedAt: new Date(),
    }

    await conversationStore.save(newSession)
    setSessions((prev) => [newSession, ...prev])
    setActiveSessionId(newSession.id)

    return newSession
  }, [])

  /**
   * Carrega a sessão pelo ID e a retorna.
   */
  const selectSession = useCallback(
    async (id: string): Promise<ConversationSession | null> => {
      const session = await conversationStore.get(id)
      if (session) {
        setActiveSessionId(id)
      }
      return session
    },
    []
  )

  /**
   * Salva a sessão no store e atualiza a lista local.
   */
  const saveCurrentSession = useCallback(
    async (session: ConversationSession): Promise<void> => {
      await conversationStore.save(session)
      setSessions((prev) =>
        prev.map((s) => (s.id === session.id ? session : s))
      )
    },
    []
  )

  /**
   * Remove a sessão do store e da lista local.
   */
  const deleteSession = useCallback(
    async (id: string): Promise<void> => {
      await conversationStore.delete(id)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeSessionId === id) {
        setActiveSessionId(null)
      }
    },
    [activeSessionId]
  )

  /**
   * Carrega as mensagens de uma sessão no useChat.
   * @param messages - Mensagens da sessão a serem carregadas
   */
  const loadMessages = useCallback(
    async (messages: Message[]): Promise<void> => {
      // Esta função será chamada pelo useChat para carregar mensagens
      // A lógica real de carregamento está no useChat
    },
    []
  )

  // Carrega as sessões ao montar o hook
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // Se não houver nenhuma sessão depois do carregamento, cria uma automaticamente
  useEffect(() => {
    if (hasLoadedSessions && sessions.length === 0 && activeSessionId === null) {
      createSession()
    }
  }, [hasLoadedSessions, sessions.length, activeSessionId, createSession])

  return {
    sessions,
    activeSessionId,
    loadSessions,
    createSession,
    selectSession,
    saveCurrentSession,
    deleteSession,
    loadMessages,
  }
}
