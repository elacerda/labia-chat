// Componente StatusBadge para exibição do status do servidor
import { ServerStatus } from '@/types'

/**
 * Props do componente StatusBadge
 */
interface StatusBadgeProps {
  status: ServerStatus
  latencyMs: number
}

/**
 * Componente que exibe o status do servidor vLLM com indicador visual
 * 
 * @param status - Status atual do servidor (online, slow, offline, unknown)
 * @param latencyMs - Latência em milissegundos da última verificação
 * @returns JSX com o indicador de status
 */
export function StatusBadge({ status, latencyMs }: StatusBadgeProps) {
  // Define o ícone e texto baseado no status
  const getStatusInfo = () => {
    switch (status) {
      case 'online':
        return {
          color: 'bg-[#22c55e]',
          text: 'Online',
          pulse: 'animate-pulse',
        }
      case 'slow':
        return {
          color: 'bg-[#eab308]',
          text: `Lento (${latencyMs}ms)`,
          pulse: '',
        }
      case 'offline':
        return {
          color: 'bg-[#ef4444]',
          text: 'Offline',
          pulse: '',
        }
      case 'unknown':
      default:
        return {
          color: 'bg-[#64748b]',
          text: 'Verificando...',
          pulse: 'animate-pulse',
        }
    }
  }

  const info = getStatusInfo()

  return (
    <div
      className="flex items-center space-x-2 cursor-help"
      title={`Último check: ${latencyMs}ms`}
    >
      <div
        className={`w-2 h-2 rounded-full ${info.color} ${info.pulse}`}
      />
      <span className="text-xs text-[#94a3b8]">{info.text}</span>
    </div>
  )
}
