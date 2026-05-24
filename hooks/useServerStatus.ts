// Hook para monitoramento do status do servidor vLLM
import { useState, useEffect, useCallback } from 'react'
import { ServerStatus } from '@/types'
import { checkHealth } from '@/lib/vllm-client'

/**
 * Hook que monitora o status de saúde do servidor vLLM
 * 
 * @returns Objeto com status, latência e data da última verificação
 */
export function useServerStatus() {
  // Estado interno
  const [status, setStatus] = useState<ServerStatus>('unknown')
  const [latencyMs, setLatencyMs] = useState<number>(0)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  // Função para verificar a saúde do servidor
  const checkServerHealth = useCallback(async () => {
    try {
      const result = await checkHealth()
      setStatus(result.status)
      setLatencyMs(result.latencyMs)
      setLastChecked(new Date())
    } catch (error) {
      // Em caso de erro, mantém o status anterior ou define como offline
      setStatus('offline')
      setLastChecked(new Date())
    }
  }, [])

  // Efeito para verificar o status ao montar o componente
  useEffect(() => {
    // Primeiro check imediatamente
    checkServerHealth()

    // Define intervalo de 30 segundos
    const intervalId = setInterval(checkServerHealth, 30000)

    // Cleanup ao desmontar
    return () => {
      clearInterval(intervalId)
    }
  }, [checkServerHealth])

  return { status, latencyMs, lastChecked }
}
