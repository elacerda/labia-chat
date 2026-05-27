// Componente SidebarHistory para exibir o histórico de conversas

import { ConversationSession } from '@/types'

/**
 * Formata uma data para uma string legível (DD/MM/YYYY)
 */
function formatDate(date: Date): string {
  return new Intl.DateTimeFormat('pt-BR').format(date)
}

/**
 * Retorna uma string relativa para a data (hoje, ontem, etc.)
 */
function getRelativeDate(date: Date): string {
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  const inputDate = new Date(date)
  inputDate.setHours(0, 0, 0, 0)

  const todayDate = new Date(today)
  todayDate.setHours(0, 0, 0, 0)

  const yesterdayDate = new Date(yesterday)
  yesterdayDate.setHours(0, 0, 0, 0)

  if (inputDate.getTime() === todayDate.getTime()) {
    return 'Hoje'
  }
  if (inputDate.getTime() === yesterdayDate.getTime()) {
    return 'Ontem'
  }
  return formatDate(date)
}

/**
 * Componente SidebarHistory para exibir o histórico de conversas.
 */
interface SidebarHistoryProps {
  sessions: ConversationSession[]
  activeSessionId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  onOpenSettings: () => void
  mode?: 'desktop' | 'mobile'
}

export function SidebarHistory({
  sessions,
  activeSessionId,
  onSelect,
  onNew,
  onDelete,
  onOpenSettings,
  mode = 'desktop',
}: SidebarHistoryProps) {
  return (
    <div
      className={`w-64 bg-[#080f1a] border-r border-[#1e293b] flex-col h-full ${
        mode === 'mobile' ? 'flex' : 'hidden md:flex'
      }`}
    >
      {/* Cabeçalho da sidebar */}
      <div className="p-4 border-b border-[#1e293b]">
        <h2 className="text-xs font-semibold text-[#94a3b8] uppercase tracking-wider">
          Histórico
        </h2>
      </div>

      {/* Botão de nova conversa */}
      <div className="p-4 border-b border-[#1e293b]">
        <button
          onClick={onNew}
          className="w-full bg-[#1D4ED8] hover:bg-[#1e40af] text-white py-2 px-4 rounded-lg text-sm font-medium transition-colors flex items-center justify-center space-x-2"
        >
          <span>+</span>
          <span>Nova conversa</span>
        </button>
      </div>

      {/* Lista de sessões com scroll */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-4 py-2 space-y-1">
        {sessions.length === 0 ? (
          <p className="text-xs text-[#64748b] text-center py-4">
            Nenhuma conversa ainda.
          </p>
        ) : (
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group relative p-3 rounded-lg cursor-pointer transition-colors flex flex-col ${
                activeSessionId === session.id
                  ? 'bg-[#1e293b]'
                  : 'hover:bg-[#1e293b]'
              }`}
              onClick={() => onSelect(session.id)}
            >
              {/* Título da sessão (truncado em 1 linha) */}
              <div className="truncate text-sm text-[#e2e8f0] font-medium mb-1">
                {session.title}
              </div>

              {/* Data relativa */}
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#94a3b8]">
                  {getRelativeDate(session.updatedAt)}
                </span>

                {/* Botão de deletar (aparece no hover) */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm('Tem certeza que deseja deletar esta conversa?')) {
                      onDelete(session.id)
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 text-[#94a3b8] hover:text-[#ef4444] transition-opacity p-1"
                  title="Deletar conversa"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Botão de limpar todas as conversas */}
      <div className="p-4 border-t border-[#1e293b]">
        <button
          onClick={() => {
            if (window.confirm('Tem certeza que deseja apagar todas as conversas? Esta ação não pode ser desfeita.')) {
              localStorage.removeItem('labia-chat-sessions');
              window.location.reload();
            }
          }}
          className="w-full flex items-center justify-center space-x-2 text-[#ef4444] hover:text-[#dc2626] hover:bg-[#fee2e2] py-2 px-4 rounded-lg text-sm font-medium transition-colors"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          <span>Limpar todas as conversas</span>
        </button>
      </div>

      {/* Rodapé da sidebar */}
      <div className="p-4 border-t border-[#1e293b]">
        <div className="flex items-center justify-between">
          <span className="text-xs text-[#94a3b8]">Pesquisador Lab-IA</span>
          <button
            onClick={onOpenSettings}
            className="text-[#94a3b8] hover:text-[#f1f5f9] transition-colors"
            title="Configurações do Sistema"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
