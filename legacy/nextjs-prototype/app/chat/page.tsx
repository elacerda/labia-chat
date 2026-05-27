'use client'

// Página de chat principal do Lab-IA
import { useState, useCallback, useEffect, useRef } from 'react'
import { useChat } from '@/hooks/useChat'
import { useConversations } from '@/hooks/useConversations'
import { ChatWindow } from '@/components/ChatWindow'
import { InputBar } from '@/components/InputBar'
import { SidebarHistory } from '@/components/SidebarHistory'
import { SystemPromptEditor } from '@/components/SystemPromptEditor'
import { useServerStatus } from '@/hooks/useServerStatus'
import { StatusBadge } from '@/components/StatusBadge'
import { ToolCallDisplay } from '@/components/ToolCallDisplay'
import { availableTools } from '@/lib/tools'
import { generateSessionTitle, generateTitleFromPrompt } from '@/lib/conversation'
import type { ConversationSession, Message } from '@/types'

// Limite máximo de tokens
const MAX_TOKENS = 65536

/**
 * Página de chat completa com sidebar, header e footer.
 * Usa o hook useChat para gerenciar o estado do chat e
 * useConversations para gerenciar as sessões de conversa.
 */
export default function ChatPage() {
  const {
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
  } = useChat()

  const { status, latencyMs } = useServerStatus()

  const {
    sessions,
    activeSessionId,
    loadSessions,
    createSession,
    selectSession,
    saveCurrentSession,
    deleteSession,
  } = useConversations()

  const [showSystemPrompt, setShowSystemPrompt] = useState(false)
  const [showErrorBanner, setShowErrorBanner] = useState(false)
  const [showMobileMenu, setShowMobileMenu] = useState(false)
  const pendingSessionLoadRef = useRef<{
    id: string
    messages: Message[]
  } | null>(null)
  const activeSessionRef = useRef<string | null>(null)
  const currentSessionRef = useRef<ConversationSession | null>(null)

  useEffect(() => {
    activeSessionRef.current = activeSessionId
  }, [activeSessionId])

  // Efeito para mostrar o banner de erro automaticamente
  useEffect(() => {
    if (error) {
      setShowErrorBanner(true)
      // Esconde o banner após 8 segundos
      const timer = setTimeout(() => {
        setShowErrorBanner(false)
      }, 8000)
      return () => clearTimeout(timer)
    }
  }, [error])

  // Salva o novo system prompt
  const handleSaveSystemPrompt = (newPrompt: string) => {
    if (newPrompt.trim()) {
      setSystemPrompt(newPrompt.trim())
      // Salva a sessão atual após alterar o system prompt
      if (activeSessionId) {
        // Encontra a sessão atual e atualiza
        const session = sessions.find((s) => s.id === activeSessionId)
        if (session) {
          saveCurrentSession(session)
        }
      }
    }
  }

  // Ao trocar de sessão, carrega as mensagens no useChat
  const handleSelectSession = useCallback(
    async (id: string) => {
      const session = await selectSession(id)
      if (session && session.messages) {
        activeSessionRef.current = session.id
        currentSessionRef.current = session
        pendingSessionLoadRef.current = {
          id: session.id,
          messages: session.messages,
        }
        loadMessages(session.messages)
      }
    },
    [selectSession, loadMessages]
  )

  // Ao criar nova sessão, carrega as mensagens no useChat
  const handleNewSession = useCallback(async () => {
    const newSession = await createSession()
    if (newSession.messages) {
      activeSessionRef.current = newSession.id
      currentSessionRef.current = newSession
      pendingSessionLoadRef.current = {
        id: newSession.id,
        messages: newSession.messages,
      }
      loadMessages(newSession.messages)
    }
  }, [createSession, loadMessages])

  // Ao deletar uma sessão, carrega a lista atualizada
  const handleDeleteSession = useCallback(
    async (id: string) => {
      await deleteSession(id)
      if (activeSessionRef.current === id) {
        activeSessionRef.current = null
        currentSessionRef.current = null
      }
      // Se a sessão deletada era a ativa, carrega a lista de sessões
      if (activeSessionId === id) {
        await loadSessions()
      }
    },
    [deleteSession, activeSessionId, loadSessions]
  )

  // Ao enviar uma mensagem, salva a sessão atual
  const handleSendMessage = useCallback(
    async (userInput: string) => {
      const sessionId = activeSessionRef.current || activeSessionId
      const currentSession = currentSessionRef.current
      let session = currentSession && currentSession.id === sessionId
        ? currentSession
        : sessionId
          ? sessions.find((s) => s.id === sessionId) || null
          : null

      if (!session) {
        session = await createSession()
        activeSessionRef.current = session.id
        currentSessionRef.current = session
      }

      const sessionHasUserPrompt = session.messages.some(
        (message) => message.role === 'user'
      )
      const baseMessages = sessionHasUserPrompt ? messages : session.messages

      if (!sessionHasUserPrompt) {
        const title = generateTitleFromPrompt(userInput)
        const titledSession = {
          ...session,
          title,
          messages: baseMessages,
          updatedAt: new Date(),
        }
        session = titledSession
        currentSessionRef.current = titledSession
        await saveCurrentSession(titledSession)
      }

      // Envia a mensagem (isso atualiza o estado interno do useChat)
      await sendMessage(userInput, availableTools, baseMessages)
    },
    [
      sendMessage,
      activeSessionId,
      sessions,
      createSession,
      saveCurrentSession,
      messages,
    ]
  )

  // Envia uma sugestão como mensagem do usuário
  const handleSuggestion = (text: string) => {
    void handleSendMessage(text)
  }

  // Sincroniza a sessão quando as mensagens mudam.
  useEffect(() => {
    if (activeSessionId && sessions.length > 0) {
      const pendingSessionLoad = pendingSessionLoadRef.current
      if (pendingSessionLoad) {
        if (pendingSessionLoad.id !== activeSessionId) {
          return
        }

        if (pendingSessionLoad.messages !== messages) {
          return
        }

        pendingSessionLoadRef.current = null
      }

      const session = sessions.find((s) => s.id === activeSessionId)
      if (session) {
        const title = generateSessionTitle(messages)
        const hasNewTitle = title !== session.title
        const hasNewMessages = session.messages !== messages

        if (hasNewMessages || hasNewTitle) {
          const updatedSession = {
            ...session,
            messages,
            title,
            updatedAt: new Date(),
          }
          currentSessionRef.current = updatedSession
          saveCurrentSession(updatedSession)
        }
      }
    }
  }, [messages, activeSessionId, sessions, saveCurrentSession])

  // Carrega as sessões ao montar o componente
  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  return (
    <div className="flex flex-col h-screen bg-[#0f172a] text-[#f1f5f9]">
      {/* Layout principal: sidebar + chat */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar com histórico de conversas */}
        <SidebarHistory
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelect={handleSelectSession}
          onNew={handleNewSession}
          onDelete={handleDeleteSession}
          onOpenSettings={() => setShowSystemPrompt(true)}
        />

        {/* Área principal de chat */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Header fixo */}
          <header className="bg-[#080f1a] border-b border-[#1e293b] px-4 md:px-6 py-3 md:py-4 flex items-center justify-between shrink-0">
            <div className="flex items-center space-x-4">
              {/* Botão hamburger para mobile */}
              <button
                onClick={() => setShowMobileMenu(!showMobileMenu)}
                className="md:hidden text-[#94a3b8] hover:text-white transition-colors"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              </button>
              <div>
                <h1 className="text-lg md:text-xl font-bold text-white">
                  Lab-IA <span className="text-[#60a5fa]">·</span> CBPF
                </h1>
                <p className="text-xs text-[#94a3b8] mt-0.5">
                  Powered by Qwen3-Coder-Next
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3 md:space-x-4">
              {/* StatusBadge - Etapa 4 */}
              <StatusBadge status={status} latencyMs={latencyMs} />
            </div>
          </header>

          {/* Banner de erro (exibido quando há erro de rede) */}
          {showErrorBanner && error && (
            <div className="bg-[#7f1d1d] border-b border-[#ef4444] px-4 md:px-6 py-2 md:py-3 flex items-center justify-between">
              <span className="text-[#fca5a5] text-sm">
                {error}
              </span>
              <button
                onClick={() => setShowErrorBanner(false)}
                className="text-[#fca5a5] hover:text-white text-sm font-medium"
              >
                Fechar
              </button>
            </div>
          )}

          {/* Corpo do chat com scroll */}
          <main className="flex-1 overflow-hidden flex flex-col">
            <ChatWindow
              messages={messages}
              isStreaming={isStreaming}
              onSuggestion={handleSuggestion}
            />
            {/* Exibe o ToolCallDisplay quando há tool calls em execução */}
            {toolCallState && (
              <ToolCallDisplay
                toolCall={toolCallState.toolCall}
                result={toolCallState.result}
                isExecuting={toolCallState.isExecuting}
              />
            )}
          </main>

          {/* Footer fixo */}
          <footer className="bg-[#0f172a] border-t border-[#1e293b] py-2 shrink-0">
            <p className="text-center text-xs text-[#64748b]">
              Laboratório de IA — CBPF · Uso interno
            </p>
          </footer>

          {/* Barra de input */}
          <InputBar
            onSend={handleSendMessage}
            isStreaming={isStreaming}
            onStop={stopGeneration}
            tokenCount={tokenCount}
            maxTokens={MAX_TOKENS}
          />
        </div>
      </div>

      {/* Overlay para mobile menu */}
      {showMobileMenu && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setShowMobileMenu(false)}
          />
          <div className="absolute left-0 top-0 bottom-0 w-64 bg-[#080f1a] border-r border-[#1e293b] p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Lab-IA · CBPF</h2>
              <button
                onClick={() => setShowMobileMenu(false)}
                className="text-[#94a3b8] hover:text-white"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
            <SidebarHistory
              sessions={sessions}
              activeSessionId={activeSessionId}
              onSelect={(id) => {
                handleSelectSession(id)
                setShowMobileMenu(false)
              }}
              onNew={() => {
                handleNewSession()
                setShowMobileMenu(false)
              }}
              onDelete={handleDeleteSession}
              onOpenSettings={() => {
                setShowSystemPrompt(true)
                setShowMobileMenu(false)
              }}
              mode="mobile"
            />
          </div>
        </div>
      )}

      {/* Modal para editar system prompt */}
      <SystemPromptEditor
        currentPrompt={messages.find((m) => m.role === 'system')?.content || ''}
        onSave={handleSaveSystemPrompt}
        isOpen={showSystemPrompt}
        onClose={() => setShowSystemPrompt(false)}
      />
    </div>
  )
}
