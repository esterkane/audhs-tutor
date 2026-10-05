import { afterEach, expect, it, vi } from 'vitest'
import { streamTutor } from './streamTutor'
import { askTutor, type TutorRequest } from './api'

const body: TutorRequest = {
  session_id: 's',
  exercise: 'Task',
  code: '',
  intent: 'explain',
  prefer_saved: false,
  questioning_style: 'explicit',
  question: 'Explain',
  output: '',
  output_stale: false,
}
afterEach(() => vi.unstubAllGlobals())

it('delivers split UTF-8 tokens before done and retains the original key', async () => {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const fetcher = vi.fn().mockResolvedValue(
    new Response(
      new ReadableStream({
        start(c) {
          controller = c
        },
      }),
    ),
  )
  vi.stubGlobal('fetch', fetcher)
  const token = vi.fn()
  const promise = streamTutor(body, new AbortController().signal, 'original-key', token)
  const bytes = new TextEncoder().encode('event: token\ndata: {"text":"für"}\n\n')
  for (const byte of bytes) controller.enqueue(new Uint8Array([byte]))
  await vi.waitFor(() => expect(token).toHaveBeenCalledWith('für'))
  controller.enqueue(
    new TextEncoder().encode('event: done\ndata: {"turn_id":"t","text":"Final wording"}\n\n'),
  )
  const result = await promise
  expect(result.text).toBe('Final wording')
  expect(fetcher.mock.calls[0][1].headers['Idempotency-Key']).toBe('original-key')
})

it('does not mistake an interrupted preview for completion', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response('event: token\ndata: {"text":"partial"}\n\n')),
  )
  const token = vi.fn()
  await expect(streamTutor(body, new AbortController().signal, 'k', token)).rejects.toThrow(
    'before completion',
  )
  expect(token).toHaveBeenCalledWith('partial')
})

it('keeps structured answer checks on the buffered endpoint', async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(
      new Response(JSON.stringify({ text: 'Checked' }), { headers: { 'Content-Type': 'application/json' } }),
    )
  vi.stubGlobal('fetch', fetcher)
  const token = vi.fn()
  await askTutor(
    { ...body, intent: 'check_answer', learner_answer: 'Answer' },
    new AbortController().signal,
    'k',
    token,
  )
  expect(fetcher.mock.calls[0][0]).toBe('/api/playground/tutor')
  expect(token).not.toHaveBeenCalled()
})
