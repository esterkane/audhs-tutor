import { afterEach, expect, it, vi } from 'vitest'
import { fetchSkills } from './api'

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
function hangingFetch() {
  const fetchMock = vi.fn(
    (_path: string, init: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {
          once: true,
        })
      }),
  )
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}
it('bounds a stalled lesson check and allows a fresh successful retry', async () => {
  vi.useFakeTimers()
  const fetchMock = hangingFetch()
  const failed = expect(fetchSkills(new AbortController().signal)).rejects.toMatchObject({
    code: 'lesson_check_timeout',
  })
  await vi.advanceTimersByTimeAsync(15_000)
  await failed
  fetchMock.mockImplementationOnce(
    async () => new Response(JSON.stringify({ skills: [], next_skill_id: null })),
  )
  await expect(fetchSkills(new AbortController().signal)).resolves.toEqual({
    skills: [],
    next_skill_id: null,
  })
  expect(vi.getTimerCount()).toBe(0)
})
it('cancels the network read when the query is cancelled, without calling it a timeout', async () => {
  vi.useFakeTimers()
  hangingFetch()
  const controller = new AbortController()
  const failed = expect(fetchSkills(controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
  controller.abort()
  await failed
  expect(vi.getTimerCount()).toBe(0)
})
