import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { AnswerReplacement } from './AnswerReplacement'
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })
it('requires review, saves explicitly and allows undo with current revision', async () => {
  let state = { replacement_id: null as string | null, revision: 0 }
  const writes: unknown[] = []
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'PUT') { const body = JSON.parse(String(init.body)); writes.push(body); state = { replacement_id: body.replacement_id, revision: state.revision + 1 } }
    return jsonResponse(state)
  }))
  renderApp(<AnswerReplacement answerId="parent" candidateId="child" />)
  fireEvent.click(screen.getByText('Review this correction as your preferred reply'))
  const choose = await screen.findByRole('button', { name: 'Prefer this correction' })
  expect(choose).toBeDisabled()
  expect(writes).toEqual([])
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(choose)
  expect(await screen.findByText('Preferred correction saved. Both answers remain in history.')).toBeVisible()
  expect(writes).toEqual([{ replacement_id: 'child', revision: 0 }])
  expect(screen.getByRole('link', { name: 'Open preferred correction' })).toHaveAttribute('href', '/answers/child')
  fireEvent.click(screen.getByRole('button', { name: 'Undo preferred correction' }))
  expect(await screen.findByText('Preference removed. Existing feedback still applies.')).toBeVisible()
  expect(writes[1]).toEqual({ replacement_id: null, revision: 1 })
})
it('keeps a failed choice explicit and requires review again after refetch', async () => {
  let revision = 0
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => init?.method === 'PUT'
    ? jsonResponse({ error: { message: 'Conflict' } }, 409)
    : jsonResponse({ replacement_id: null, revision: revision++ })))
  renderApp(<AnswerReplacement answerId="parent" candidateId="child" />)
  fireEvent.click(screen.getByText('Review this correction as your preferred reply'))
  fireEvent.click(await screen.findByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Prefer this correction' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be confirmed')
  fireEvent.click(screen.getByRole('button', { name: 'Review latest saved choice' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Prefer this correction' })).toBeDisabled())
})

it('releases a stalled write and ignores its late response after a successful retry', async () => {
  let release!: (value: Response) => void
  let puts = 0
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method !== 'PUT') return jsonResponse({ replacement_id: null, revision: 0 })
    puts++
    if (puts === 1) return new Promise<Response>((resolve) => { release = resolve })
    return jsonResponse({ replacement_id: 'child', revision: 1 })
  }))
  renderApp(<AnswerReplacement answerId="parent" candidateId="child" />)
  fireEvent.click(screen.getByText('Review this correction as your preferred reply'))
  fireEvent.click(await screen.findByRole('checkbox'))
  vi.useFakeTimers()
  fireEvent.click(screen.getByRole('button', { name: 'Prefer this correction' }))
  await act(async () => { await vi.advanceTimersByTimeAsync(15001) })
  vi.useRealTimers()
  expect(screen.getByRole('alert')).toHaveTextContent('could not be confirmed')
  fireEvent.click(screen.getByRole('button', { name: 'Prefer this correction' }))
  expect(await screen.findByText('Preferred correction saved. Both answers remain in history.')).toBeVisible()
  await act(async () => { release(jsonResponse({ replacement_id: 'wrong', revision: 99 })) })
  expect(screen.getByRole('link', { name: 'Open preferred correction' })).toHaveAttribute('href', '/answers/child')
})
