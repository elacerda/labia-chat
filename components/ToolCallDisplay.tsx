// Componente ToolCallDisplay para exibir chamadas de ferramenta
import { ToolCall } from '@/types'

/**
 * Props do componente ToolCallDisplay
 */
interface ToolCallDisplayProps {
  toolCall: ToolCall
  result: string | null
  isExecuting: boolean
}

/**
 * Formata um objeto de argumentos como JSON indentado
 * 
 * @param args - Objeto de argumentos
 * @returns String JSON formatada com indentação de 2 espaços
 */
function formatArgs(args: object): string {
  return JSON.stringify(args, null, 2)
}

/**
 * Componente que exibe uma chamada de ferramenta em execução ou com resultado
 * 
 * @param toolCall - A chamada de ferramenta a ser exibida
 * @param result - Resultado da execução (null se ainda não executou)
 * @param isExecuting - Indica se a ferramenta está em execução
 * @returns JSX com a visualização da tool call
 */
export function ToolCallDisplay({
  toolCall,
  result,
  isExecuting,
}: ToolCallDisplayProps) {
  // Parse dos argumentos para exibição
  let argsObject: object = {}
  try {
    argsObject = JSON.parse(toolCall.function.arguments)
  } catch (error) {
    // Se falhar, usa objeto vazio
  }

  return (
    <div className="border-l-4 border-blue-600 bg-slate-900 rounded-r-lg p-4 my-2">
      {/* Cabeçalho com ícone e nome da função */}
      <div className="flex items-center space-x-2 mb-3">
        <span className="text-lg">🔧</span>
        <span className="font-bold text-slate-200">
          {toolCall.function.name}
        </span>
      </div>

      {/* Argumentos formatados como JSON */}
      <div className="mb-3">
        <span className="text-xs text-slate-500 uppercase font-semibold">
          Argumentos:
        </span>
        <pre className="bg-slate-950 p-2 rounded mt-1 text-xs font-mono text-slate-300 overflow-x-auto">
          {formatArgs(argsObject)}
        </pre>
      </div>

      {/* Estado de execução ou resultado */}
      {isExecuting ? (
        <div className="flex items-center space-x-2 text-blue-400 text-sm">
          <svg
            className="animate-spin h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Executando ferramenta...</span>
        </div>
      ) : result ? (
        <div>
          <span className="text-xs text-slate-500 uppercase font-semibold">
            Resultado:
          </span>
          <pre className="bg-slate-950 p-2 rounded mt-1 text-xs font-mono text-slate-300 overflow-x-auto whitespace-pre-wrap">
            {result}
          </pre>
        </div>
      ) : null}
    </div>
  )
}
