'use client'

// Componente InputBar para enviar mensagens
import React, { useState, useRef, useLayoutEffect } from 'react'

// Tipos de props
interface InputBarProps {
  onSend: (text: string) => void
  isStreaming: boolean
  onStop: () => void
  tokenCount: number
  maxTokens: number
}

/**
 * Componente que exibe a barra de input para enviar mensagens.
 * Inclui textarea que expande automaticamente, botões de enviar/parar
 * e contador de tokens.
 */
export function InputBar({
  onSend,
  isStreaming,
  onStop,
  tokenCount,
  maxTokens,
}: InputBarProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const collapsedHeight = 48
  const expandedHeight = 144

  // Ajusta a altura do textarea automaticamente
  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = `${collapsedHeight}px`
    const shouldExpand = textarea.scrollHeight > collapsedHeight
    const nextHeight = shouldExpand ? expandedHeight : collapsedHeight
    textarea.style.height = `${nextHeight}px`
    textarea.style.overflowY =
      textarea.scrollHeight > expandedHeight ? 'auto' : 'hidden'
  }, [text])

  // Envia a mensagem ao pressionar Enter (sem Shift)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Envia a mensagem
  const handleSubmit = () => {
    if (text.trim() === '') return
    onSend(text.trim())
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = `${collapsedHeight}px`
      textareaRef.current.style.overflowY = 'hidden'
    }
  }

  // Calcula a cor do contador de tokens
  const getTokenColor = () => {
    const percentage = (tokenCount / maxTokens) * 100
    if (percentage >= 85) return 'text-[#ef4444]'
    if (percentage >= 70) return 'text-[#eab308]'
    return 'text-[#94a3b8]'
  }

  return (
    <div className="bg-[#1e293b] border-t border-[#475569] p-3 md:p-4">
      <div className="max-w-4xl mx-auto relative">
        {/* Área do textarea */}
        <div className="relative">
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isStreaming}
            placeholder={
              isStreaming
                ? 'Aguardando resposta...'
                : 'Digite sua mensagem...'
            }
            className="hide-scrollbar w-full bg-transparent text-[#f1f5f9] placeholder-[#94a3b8] rounded-xl px-4 py-3 pr-24 resize-none focus:outline-none focus:ring-2 focus:ring-[#1D4ED8] disabled:opacity-50 min-h-[48px]"
            style={{ height: collapsedHeight }}
          />

          {/* Botão de ação (Enviar ou Parar) */}
          <div className="absolute bottom-3 right-3">
            {isStreaming ? (
              <button
                onClick={onStop}
                className="bg-[#dc2626] hover:bg-[#b91c1c] text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
                  />
                </svg>
                <span>Parar</span>
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={text.trim() === ''}
                className="bg-[#2563eb] hover:bg-[#1d4ed8] disabled:bg-[#475569] disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors flex items-center space-x-2"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
                <span>Enviar</span>
              </button>
            )}
          </div>
        </div>

        {/* Contador de tokens */}
        <div className="flex justify-end mt-2">
          <span className={`text-xs ${getTokenColor()}`}>
            ~{tokenCount} / {maxTokens} tokens
          </span>
        </div>
      </div>
    </div>
  )
}
