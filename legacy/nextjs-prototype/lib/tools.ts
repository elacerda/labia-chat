// Definição e execução de ferramentas para o Chat Lab-IA

/**
 * Definição da ferramenta de busca na documentação
 */
export const searchDocsTool = {
  type: 'function' as const,
  function: {
    name: 'search_docs',
    description:
      'Busca informacoes na documentacao tecnica do laboratorio e em referencias de bibliotecas Python comuns (numpy, pandas, pytorch, scikit-learn).',
    parameters: {
      type: 'object' as const,
      required: ['query'] as const,
      properties: {
        query: {
          type: 'string' as const,
          description: 'Termo ou pergunta a buscar',
        },
      },
    },
  },
}

/**
 * Executa a busca na documentação (stub para esta etapa)
 * 
 * @param args - Argumentos da ferramenta (query)
 * @returns Texto simulado do resultado da busca
 */
export async function executeSearchDocs(
  args: { query: string }
): Promise<string> {
  // Em produção, este stub deve ser substituído por uma chamada real
  // a uma base de conhecimento ou API de busca
  return `Resultado da busca por '${args.query}': Esta e uma resposta de demonstracao. Em producao, este stub deve ser substituido por uma chamada real a uma base de conhecimento ou API de busca.`
}

/**
 * Dispatcher geral para execução de ferramentas
 * 
 * @param name - Nome da ferramenta a ser executada
 * @param argumentsJson - Argumentos em formato JSON string
 * @returns Resultado da execução da ferramenta ou mensagem de erro
 */
export async function executeTool(
  name: string,
  argumentsJson: string
): Promise<string> {
  try {
    // Faz o parse dos argumentos JSON
    const args = JSON.parse(argumentsJson)

    // Chama a função correta com base no nome
    switch (name) {
      case 'search_docs':
        return await executeSearchDocs(args)
      default:
        return `Ferramenta desconhecida: ${name}`
    }
  } catch (error) {
    // Tratamento de erro para JSON inválido
    if (error instanceof SyntaxError) {
      return `Erro ao parsear argumentos da ferramenta: ${error.message}`
    }
    return `Erro ao executar ferramenta: ${error instanceof Error ? error.message : String(error)}`
  }
}

/**
 * Lista de ferramentas disponíveis para enviar à API
 */
export const availableTools = [searchDocsTool]
