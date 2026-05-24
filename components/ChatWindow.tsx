'use client'

// Componente ChatWindow para exibir o histórico de mensagens
import React, { useRef, useEffect } from 'react'
import { Message } from '@/types'
import { MessageBubble } from './MessageBubble'

// Tipos de props
interface ChatWindowProps {
  messages: Message[]
  isStreaming: boolean
  onSuggestion?: (text: string) => void
}

/**
 * Componente que exibe a janela de chat com todas as mensagens.
 * Inclui scroll automático e tela de boas-vindas quando não há mensagens.
 */
export function ChatWindow({ messages, isStreaming, onSuggestion }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  // Scroll automático para o final sempre que messages mudar
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // Sugestões de prompts para a tela de boas-vindas
  const suggestions = [
    'Escreva um script Python para ler um CSV com pandas',
    'Explique o algoritmo de atencao dos transformers',
    'Como configuro um ambiente virtual Python no Linux?',
  ]

  // Verifica se há apenas o system prompt (sem mensagens de usuário)
  const isEmpty = messages.length <= 1

  return (
    <div
      ref={scrollContainerRef}
      className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 scroll-smooth bg-[#0f172a]"
    >
      {/* Tela de boas-vindas quando não há mensagens */}
      {isEmpty && (
        <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-4">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Lab-IA · CBPF
          </h1>
          <p className="text-lg text-[#94a3b8] mb-8 max-w-md">
            Como posso ajudar sua pesquisa hoje?
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl w-full">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => onSuggestion?.(suggestion)}
                className="text-left p-4 rounded-xl bg-[#1e293b] hover:bg-[#334155] border border-[#475569] hover:border-[#64748b] transition-all duration-200 group"
              >
                <p className="text-[#e2e8f0] text-sm font-medium group-hover:text-white">
                  {suggestion}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Lista de mensagens */}
      <div className="space-y-2">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {/* Cursor de streaming animado */}
        {isStreaming && messages.length > 0 && (
          <div className="flex items-start space-x-2 animate-pulse">
            <div className="w-8 h-8 rounded-full bg-[#334155] flex-shrink-0 flex items-center justify-center">
              <span className="text-xs text-[#cbd5e1]">IA</span>
            </div>
            <div className="bg-[#1e293b] px-4 py-2 rounded-2xl rounded-tl-none border border-[#475569]">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-[#94a3b8] rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-[#94a3b8] rounded-full animate-bounce delay-75" />
                <div className="w-2 h-2 bg-[#94a3b8] rounded-full animate-bounce delay-150" />
              </div>
            </div>
          </div>
        )}

        {/* Ref para scroll automático */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}
