// Componente SystemPromptEditor para editar o system prompt
import { useState, useEffect } from 'react'

/**
 * Modal para editar o system prompt.
 * Pode ser fechado clicando fora (overlay) ou pressionando Escape.
 */
interface SystemPromptEditorProps {
  currentPrompt: string
  onSave: (newPrompt: string) => void
  isOpen: boolean
  onClose: () => void
}

export function SystemPromptEditor({
  currentPrompt,
  onSave,
  isOpen,
  onClose,
}: SystemPromptEditorProps) {
  const [promptValue, setPromptValue] = useState(currentPrompt)

  // Atualiza o valor local quando o prompt externo muda
  useEffect(() => {
    setPromptValue(currentPrompt)
  }, [currentPrompt])

  // Fecha ao pressionar Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    if (isOpen) {
      window.addEventListener('keydown', handleEscape)
    }
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Fecha ao clicar no overlay
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const handleSave = () => {
    onSave(promptValue)
  }

  if (!isOpen) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
      onClick={handleOverlayClick}
    >
      <div className="bg-[#0f172a] border border-slate-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4 flex flex-col max-h-[90vh]">
        {/* Cabeçalho do modal */}
        <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Editar System Prompt</h3>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
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

        {/* Conteúdo do modal */}
        <div className="px-6 py-4 flex-1 overflow-y-auto">
          <div className="mb-4">
            <textarea
              value={promptValue}
              onChange={(e) => setPromptValue(e.target.value)}
              className="w-full bg-[#0b1120] border border-slate-700 rounded-md p-3 text-slate-200 font-mono text-sm focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none"
              rows={12}
              placeholder="Digite o system prompt aqui..."
            />
          </div>

          {/* Aviso sobre o system prompt */}
          <div className="bg-blue-900 bg-opacity-30 border border-blue-800 rounded-md p-3">
            <p className="text-xs text-blue-200">
              <strong>Aviso:</strong> O system prompt é sempre enviado ao modelo como
              primeira instrução. Alterar pode mudar o comportamento do assistente
              para toda a conversa atual.
            </p>
          </div>
        </div>

        {/* Rodapé do modal com botões */}
        <div className="px-6 py-4 border-t border-slate-700 flex items-center justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-700 rounded-md text-sm font-medium transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors"
          >
            Salvar
          </button>
        </div>
      </div>
    </div>
  )
}
