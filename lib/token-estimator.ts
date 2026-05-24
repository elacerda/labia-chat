// Estimador de tokens para o Chat Lab-IA
// Importe o tipo Message de types/index.ts
import { Message } from '@/types'

/**
 * Estima o número de tokens em um texto.
 * 
 * Implementação simples baseada na relação aproximada de 4 caracteres = 1 token.
 * Para produção, seria ideal usar a biblioteca tiktoken com o tokenizer específico
 * do modelo qwen-coder-next para uma estimativa mais precisa.
 * 
 * @param text - Texto para estimar o número de tokens
 * @returns Número estimado de tokens
 */
export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4)
}

/**
 * Estima o número total de tokens em um array de mensagens.
 * 
 * Soma o número de tokens de cada mensagem (content) e adiciona
 * uma sobrecarga fixa de 4 tokens por mensagem para considerar
 * o overhead do formatação do chat template.
 * 
 * @param messages - Array de mensagens
 * @returns Número total estimado de tokens
 */
export function estimateMessagesTokens(messages: Message[]): number {
  const contentTokens = messages.reduce(
    (total, msg) => total + estimateTokens(msg.content),
    0
  )
  // Sobrecarga fixa de 4 tokens por mensagem (overhead do chat template)
  const overhead = messages.length * 4
  return contentTokens + overhead
}

/**
 * Verifica se o contexto precisa ser truncado.
 * 
 * @param messages - Array de mensagens
 * @param limitTokens - Limite máximo de tokens permitido
 * @returns true se o número de tokens exceder o limite
 */
export function shouldTrimContext(messages: Message[], limitTokens: number): boolean {
  return estimateMessagesTokens(messages) > limitTokens
}

/**
 * Trunca o contexto mantendo apenas as mensagens mais recentes.
 * 
 * IMPORTANTE: Preserva sempre a primeira mensagem (geralmente o system prompt).
 * Remove mensagens antigas do meio até o total ficar abaixo do limite,
 * mantendo sempre as últimas keepLastN mensagens além do system prompt.
 * 
 * @param messages - Array de mensagens original
 * @param limitTokens - Limite máximo de tokens (55.000 para este projeto)
 * @param keepLastN - Número de mensagens recentes a manter além do system prompt
 * @returns Array de mensagens truncado
 */
export function trimContext(
  messages: Message[],
  limitTokens: number,
  keepLastN: number = 10
): Message[] {
  // Se o contexto já está dentro do limite, retorna sem modificações
  if (!shouldTrimContext(messages, limitTokens)) {
    return messages
  }

  // Preserva o system prompt (primeira mensagem, se for role "system")
  const systemPrompt = messages[0]?.role === 'system' ? [messages[0]] : []
  
  // Remove o system prompt para trabalhar apenas com as mensagens de conversa
  const conversationMessages = messages.slice(systemPrompt.length)
  
  // Mantém as últimas keepLastN mensagens
  const recentMessages = conversationMessages.slice(-keepLastN)
  
  // Se já estiver dentro do limite com as mensagens recentes, retorna
  if (!shouldTrimContext([...systemPrompt, ...recentMessages], limitTokens)) {
    return [...systemPrompt, ...recentMessages]
  }

  // Se ainda estiver acima do limite, remove mensagens do início das recentes
  // até ficar dentro do limite
  let trimmed = [...recentMessages]
  while (shouldTrimContext([...systemPrompt, ...trimmed], limitTokens) && trimmed.length > 0) {
    trimmed.shift()
  }

  return [...systemPrompt, ...trimmed]
}
