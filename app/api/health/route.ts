import { NextResponse } from 'next/server'

import { ServerStatus } from '@/types'

const BASE_URL = process.env.VLLM_BASE_URL

export async function GET() {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 8000)
  const startTime = Date.now()

  try {
    const response = await fetch(`${BASE_URL}/health`, {
      method: 'GET',
      signal: controller.signal,
      cache: 'no-store',
    })
    const latencyMs = Date.now() - startTime
    const status: ServerStatus = response.ok
      ? latencyMs < 5000
        ? 'online'
        : 'slow'
      : 'offline'

    return NextResponse.json({ status, latencyMs })
  } catch {
    return NextResponse.json(
      { status: 'offline', latencyMs: Date.now() - startTime },
      { status: 200 }
    )
  } finally {
    clearTimeout(timeoutId)
  }
}
