import { afterEach, expect, test, vi } from 'vitest'
import { t } from './i18n'
import { ApiError, TutorApi, turnErrorMessage } from './api'

afterEach(() => vi.unstubAllGlobals())
function client(body: BodyInit) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(new Response(body, { headers: { 'Content-Type': 'text/event-stream' } })),
  )
  return new TutorApi('/synthetic-project', async () => null)
}

test('premature stream EOF is a failure rather than an indefinitely pending answer', async () => {
  const api = client('event: token\ndata: {"text":"Partial explanation"}\n\n')
  const event = vi.fn()
  await expect(api.turn('session', 'Preserve my question', event)).rejects.toMatchObject({ status: 502 })
  expect(event).toHaveBeenCalledWith({ event: 'token', data: { text: 'Partial explanation' } })
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('complete turn is delivered once without retrying', async () => {
  const api = client('event: turn\ndata: {"turn_id":"answer","turn":{"text":"Complete"}}\n\n')
  const event = vi.fn()
  await api.turn('session', 'Question', event)
  expect(event).toHaveBeenCalledTimes(1)
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('explicit server error is delivered without replacing it with an EOF error', async () => {
  const api = client('event: error\ndata: {"message":"Budget reached"}\n\n')
  const event = vi.fn()
  await api.turn('session', 'Question', event)
  expect(event).toHaveBeenCalledWith({ event: 'error', data: { message: 'Budget reached' } })
  expect(fetch).toHaveBeenCalledTimes(1)
})


test.each(['turn', 'error', 'token'] as const)('keeps the %s outcome when the connection later fails', async (kind) => {
  let control!: ReadableStreamDefaultController<Uint8Array>
  const api = client(new ReadableStream<Uint8Array>({ start(controller) { control = controller } }))
  const error = new Error('Connection interrupted')
  const event = vi.fn(() => control.error(error))
  const data = { turn: { turn_id: 'saved', turn: { text: 'Complete' } }, error: { message: 'Budget reached' }, token: { text: 'Partial' } }[kind]
  control.enqueue(new TextEncoder().encode('event: ' + kind + '\ndata: ' + JSON.stringify(data) + '\n\n'))
  const result = api.turn('session', 'Question', event)
  if (kind === 'turn') await expect(result).rejects.toThrow('Your answer was saved')
  if (kind === 'error') await expect(result).resolves.toBeUndefined()
  if (kind === 'token') await expect(result).rejects.toMatchObject({ streamOutcome: 'incomplete' })
  expect(event).toHaveBeenCalledExactlyOnceWith({ event: kind, data })
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('localizes interrupted turns and preserves the actual provider failure', () => {
  expect(turnErrorMessage(new ApiError(502, '', 'saved'), t('de'))).toContain('gespeichert')
  expect(turnErrorMessage(new ApiError(502, '', 'incomplete'), t('de'))).toContain('Verlauf')
  for (const lang of ['de', 'en'] as const)
    expect(turnErrorMessage(new ApiError(503, 'Daily budget exhausted'), t(lang))).toBe('Daily budget exhausted')
})
