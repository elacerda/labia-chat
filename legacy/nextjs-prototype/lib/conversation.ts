// Módulo de gerenciamento de conversas para o Chat Lab-IA
// Arquitetura preparada para futura integração com banco de dados do SCoPE-AI

import { ConversationSession, Message } from '@/types'

// Chave usada no localStorage para armazenar as sessões
const STORAGE_KEY = 'labia-chat-sessions'

/**
 * Gera um ID único para sessões usando UUID v4
 */
export function generateSessionId(): string {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID()
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/**
 * Gera um título curto a partir do inicio de um prompt do usuário.
 */
export function generateTitleFromPrompt(prompt: string): string {
  const words = prompt.trim().replace(/\s+/g, ' ').split(' ').filter(Boolean)
  if (words.length === 0) return 'Nova conversa'

  const title = words.slice(0, 6).join(' ')
  return words.length > 6 ? `${title}...` : title
}

/**
 * Gera um título para a sessão a partir das primeiras 6 palavras
 * do primeiro prompt do usuário.
 */
export function generateSessionTitle(messages: Message[]): string {
  const userMessage = messages.find((m) => m.role === 'user')
  return userMessage
    ? generateTitleFromPrompt(userMessage.content)
    : 'Nova conversa'
}

/**
 * Interface que define a contract para persistência de conversas.
 * Para integrar com o banco de dados do SCoPE-AI, basta criar uma classe
 * ApiAdapter que implementa esta interface e faz chamadas REST para os
 * endpoints do site. Nenhum componente ou hook precisará ser alterado.
 */
export interface ConversationStore {
  list(): Promise<ConversationSession[]>
  get(id: string): Promise<ConversationSession | null>
  save(session: ConversationSession): Promise<void>
  delete(id: string): Promise<void>
}

/**
 * Implementação do ConversationStore usando localStorage como persistência.
 * Esta é a implementação padrão para a Etapa 3.
 */
export class LocalStorageAdapter implements ConversationStore {
  /**
   * Retorna todas as sessões ordenadas por updatedAt em ordem decrescente
   */
  async list(): Promise<ConversationSession[]> {
    // Verifica se estamos no navegador (localStorage disponível)
    if (typeof localStorage === 'undefined') {
      return []
    }

    try {
      const data = localStorage.getItem(STORAGE_KEY)
      if (!data) return []

      const sessions: ConversationSession[] = JSON.parse(data)
      // Converte strings de data de volta para objetos Date
      for (const session of sessions) {
        session.createdAt = new Date(session.createdAt)
        session.updatedAt = new Date(session.updatedAt)
        for (const message of session.messages) {
          message.createdAt = new Date(message.createdAt)
        }
      }
      // Ordena por updatedAt decrescente (mais recentes primeiro)
      return sessions.sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime())
    } catch (error) {
      console.error('Erro ao carregar sessões do localStorage:', error)
      return []
    }
  }

  /**
   * Retorna uma sessão específica pelo ID
   */
  async get(id: string): Promise<ConversationSession | null> {
    const sessions = await this.list()
    return sessions.find((s) => s.id === id) || null
  }

  /**
   * Salva uma sessão. Se já existe (mesmo id), atualiza; senão, insere.
   */
  async save(session: ConversationSession): Promise<void> {
    try {
      const sessions = await this.list()
      const existingIndex = sessions.findIndex((s) => s.id === session.id)

      if (existingIndex >= 0) {
        // Atualiza sessão existente
        sessions[existingIndex] = session
      } else {
        // Insere nova sessão
        sessions.push(session)
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    } catch (error) {
      console.error('Erro ao salvar sessão no localStorage:', error)
      throw error
    }
  }

  /**
   * Remove uma sessão pelo ID
   */
  async delete(id: string): Promise<void> {
    try {
      const sessions = await this.list()
      const filtered = sessions.filter((s) => s.id !== id)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered))
    } catch (error) {
      console.error('Erro ao deletar sessão do localStorage:', error)
      throw error
    }
  }
}

/**
 * Instância padrão do ConversationStore usando localStorage.
 * Para usar uma implementação baseada em API (para o SCoPE-AI),
 * basta substituir esta exportação por uma instância de ApiAdapter.
 */
export const conversationStore: ConversationStore = new LocalStorageAdapter()
