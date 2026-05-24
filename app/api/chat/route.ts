import { NextRequest } from 'next/server'

const BASE_URL = process.env.VLLM_BASE_URL
const API_KEY = process.env.VLLM_API_KEY || 'labia-local-key'
const MODEL_ID = process.env.VLLM_MODEL_ID || 'qwen-coder-next'

export async function POST(request: NextRequest) {
  if (!BASE_URL) {
    return new Response('VLLM_BASE_URL nao configurada', { status: 500 })
  }

  const body = await request.json()

  const response = await fetch(`${baseUrlWithoutTrailingSlash(BASE_URL)}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${API_KEY}`,
    },
    body: JSON.stringify({
      ...body,
      model: MODEL_ID,
      stream: true,
    }),
  })

  if (!response.ok) {
    return new Response(await response.text(), { status: response.status })
  }

  if (!response.body) {
    return new Response('Resposta do vLLM sem body de streaming', { status: 502 })
  }

  return new Response(response.body, {
    status: 200,
    headers: {
      'Cache-Control': 'no-cache, no-transform',
      'Content-Type': response.headers.get('Content-Type') || 'text/event-stream',
    },
  })
}

function baseUrlWithoutTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '')
}
