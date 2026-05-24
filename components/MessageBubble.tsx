'use client'

// Componente MessageBubble para exibir mensagens no chat
import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Message } from '@/types'

// Tipos de props
interface MessageBubbleProps {
  message: Message
}

/**
 * Componente que renderiza um único balão de mensagem.
 * Suporta renderização de markdown, syntax highlighting para código
 * e diferentes estilos para cada tipo de mensagem.
 */
export function MessageBubble({ message }: MessageBubbleProps) {
  // Estado para o botão de copiar
  const [copied, setCopied] = useState(false)
  const [hoveredCodeBlock, setHoveredCodeBlock] = useState<string | null>(null)

  if (message.role === 'system') {
    return null
  }

  // Formata a data para HH:MM
  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Copia o código para a área de transferência
  const handleCopy = (code: string, language: string) => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  // Renderiza blocos de código com syntax highlighting
  const renderCodeBlock = ({
    language,
    value,
  }: {
    language?: string
    value: string
  }) => {
    const lang = language || 'text'
    return (
      <div
        className="my-4 rounded-lg overflow-hidden border border-[#475569]"
        onMouseEnter={() => setHoveredCodeBlock(lang)}
        onMouseLeave={() => setHoveredCodeBlock(null)}
      >
        {/* Cabeçalho do bloco de código */}
        <div className="flex items-center justify-between bg-[#0f172a] px-4 py-2">
          <span className="text-xs font-mono text-[#94a3b8] uppercase">
            {lang}
          </span>
          <button
            onClick={() => handleCopy(value, lang)}
            className="text-xs font-medium text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
          >
            {copied ? 'Copiado!' : 'Copiar'}
          </button>
        </div>

        {/* Código com syntax highlighting */}
        <div className="bg-[#020617] overflow-x-auto">
          <pre className="m-0 p-4 text-sm font-mono text-[#e2e8f0]">
            <code>{value}</code>
          </pre>
        </div>
      </div>
    )
  }

  // Renderiza o conteúdo da mensagem
  const renderContent = () => {
    switch (message.role) {
      case 'user':
        // Mensagens do usuário: texto simples, sem markdown
        return <p className="whitespace-pre-wrap">{message.content}</p>

      case 'assistant':
        // Mensagens do assistant: renderização de markdown
        return (
          <div className="prose prose-invert max-w-none">
            <ReactMarkdown
              components={{
                code: ({ className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || '')
                  return match ? (
                    renderCodeBlock({
                      language: match[1],
                      value: String(children).replace(/\n$/, ''),
                    })
                  ) : (
                    <code
                      className={`${className} bg-[#334155] px-1.5 py-0.5 rounded text-sm font-mono text-[#e2e8f0]`}
                      {...props}
                    >
                      {children}
                    </code>
                  )
                },
                p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                ul: ({ children }) => (
                  <ul className="list-disc pl-5 mb-2 last:mb-0">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal pl-5 mb-2 last:mb-0">{children}</ol>
                ),
                li: ({ children }) => <li className="mb-1">{children}</li>,
                h1: ({ children }) => (
                  <h1 className="text-2xl font-bold mb-3 mt-4">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-xl font-bold mb-2 mt-3">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-lg font-bold mb-2 mt-2">{children}</h3>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-[#475569] pl-4 italic text-[#cbd5e1] my-2">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="border-[#475569] my-4" />,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )

      case 'tool':
        // Mensagens de ferramenta
        return (
          <div className="bg-[#0f2027] rounded-lg p-4 border border-[#475569]">
            <p className="text-xs text-[#94a3b8] mb-2 uppercase font-semibold">
              [Resultado da ferramenta]
            </p>
            <pre className="text-xs font-mono text-[#cbd5e1] overflow-x-auto">
              {message.content}
            </pre>
          </div>
        )

      default:
        return null
    }
  }

  // Renderiza o balão de mensagem
  return (
    <div
      className={`flex flex-col ${
        message.role === 'user'
          ? 'items-end'
          : 'items-start'
      } mb-6`}
    >
      {/* Balão de mensagem */}
      <div
        className={`max-w-[72%] rounded-2xl px-5 py-3 shadow-lg ${
          message.role === 'user'
            ? 'bg-[#1D4ED8] text-white'
            : message.role === 'tool'
            ? 'bg-[#0f2027] border border-[#475569]'
            : 'bg-[#1e293b] text-[#f1f5f9]'
        }`}
      >
        {renderContent()}
      </div>

      {/* Horário da mensagem */}
      <span className="text-xs text-[#94a3b8] mt-1 ml-1">
        {formatTime(message.createdAt)}
      </span>
    </div>
  )
}
