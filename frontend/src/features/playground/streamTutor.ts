import type { TutorReply, TutorRequest } from './api'
import type { Schemas } from '../../lib/api'

/** Preview tokens are never a completed/checked reply; only done settles this promise. */
export async function streamTutor(
  body: TutorRequest,
  signal: AbortSignal,
  requestKey: string | undefined,
  onToken: (text: string) => void,
): Promise<TutorReply> {
  return streamReply('/api/playground/tutor/stream', body, signal, requestKey, onToken)
}

export function streamAnswerFollowup(
  answerId: string,
  body: Schemas['AnswerFollowup'],
  signal: AbortSignal,
  requestKey: string,
  onToken: (text: string) => void,
): Promise<TutorReply> {
  return streamReply(
    `/api/answers/${encodeURIComponent(answerId)}/followup/stream`,
    body,
    signal,
    requestKey,
    onToken,
  )
}

async function streamReply(
  endpoint: string,
  body: TutorRequest | Schemas['AnswerFollowup'],
  signal: AbortSignal,
  requestKey: string | undefined,
  onToken: (text: string) => void,
): Promise<TutorReply> {
  const response = await fetch(endpoint, {
    method: 'POST',
    signal,
    headers: { 'Content-Type': 'application/json', ...(requestKey ? { 'Idempotency-Key': requestKey } : {}) },
    body: JSON.stringify(body),
  })
  if (!response.ok || !response.body) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.error?.message || `Tutor request failed (${response.status}).`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  function dispatch(block: string): TutorReply | undefined {
    const lines = block.split('\n')
    const event = lines
      .find((line) => line.startsWith('event:'))
      ?.slice(6)
      .trim()
    const data = lines
      .filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart())
      .join('\n')
    if (!data) return
    const payload = JSON.parse(data)
    if (event === 'error') throw new Error(payload.message || 'Tutor response interrupted.')
    if (event === 'token' && typeof payload.text === 'string') onToken(payload.text)
    if (event === 'done') {
      if (typeof payload.text !== 'string' || typeof payload.turn_id !== 'string')
        throw new Error('The tutor returned an invalid completed reply.')
      return payload as TutorReply
    }
  }
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (signal.aborted) throw new DOMException('Stopped', 'AbortError')
      buffer += decoder.decode(value, { stream: !done })
      buffer = buffer.replace(/\r\n/g, '\n')
      if (buffer.length > 1_000_000) throw new Error('Tutor response exceeded the supported size.')
      let boundary: number
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const result = dispatch(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
        if (result) return result
      }
      if (done) {
        if (buffer.trim()) {
          const result = dispatch(buffer)
          if (result) return result
        }
        throw new Error(
          'The response ended before completion. Received text is retained; use request recovery.',
        )
      }
    }
  } finally {
    await reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}
