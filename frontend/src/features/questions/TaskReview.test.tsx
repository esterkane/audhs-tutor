import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { TaskReview } from './TaskReview'

const preview = { assessment_id: 'a1', content_version: 'v1', content: { objective: { title: 'Explain selection bias' }, item: { prompt: 'Who is missing?' }, criteria: [{ criterion: 'Identify excluded groups' }] }, current_review: null, approval_matches_content: false, reviewable: true, unavailable_reason: null }
afterEach(() => vi.unstubAllGlobals())

it('reveals only on request and requires explicit confirmation', async () => {
  const fetcher = vi.fn(async (_path: string, init?: RequestInit) => jsonResponse(init?.method === 'POST' ? { decision: 'approve' } : preview))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  await screen.findByText('Explain selection bias')
  expect(screen.getByRole('button', { name: 'Approve this task review' })).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Approve this task review' }))
  await screen.findByText('Task review saved. This does not change your grades or confirm understanding.')
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  expect(JSON.parse(String(fetcher.mock.calls[1][1]?.body)).confirmed).toBe(true)
})

it('retries uncertain saves with the exact command and prevents duplicate submission', async () => {
  const bodies: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => {
    if (init?.method !== 'POST') return jsonResponse(preview)
    bodies.push(String(init.body))
    if (bodies.length === 1) throw new TypeError('offline')
    return jsonResponse({ decision: 'approve' })
  }))
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  fireEvent.click(await screen.findByRole('checkbox'))
  const approve = screen.getByRole('button', { name: 'Approve this task review' })
  fireEvent.click(approve); fireEvent.click(approve)
  fireEvent.click(await screen.findByRole('button', { name: 'Retry same review' }))
  await screen.findByText('Task review saved. This does not change your grades or confirm understanding.')
  expect(bodies).toHaveLength(2)
  expect(bodies[1]).toBe(bodies[0])
})

it('clears confirmation on refresh and does not execute reference markup', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ ...preview, content: { ...preview.content, item: { prompt: '<script>bad()</script>' } } })))
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  await screen.findByText('<script>bad()</script>')
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Reload task and rubric' }))
  await waitFor(() => expect(screen.getByRole('checkbox')).not.toBeChecked())
})

it('revokes the recorded facet and requires fresh review after a conflict', async () => {
  const bodies: Array<Record<string, unknown>> = []
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      bodies.push(JSON.parse(String(init.body)))
      return jsonResponse({ error: { code: 'task_review_changed', message: 'changed' } }, 409)
    }
    return jsonResponse({ ...preview, current_review: { id: 'r1', revision: 1, decision: 'approve', facet: 'application', reviewed_at: '2026-10-12T10:00:00Z' } })
  }))
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  fireEvent.click(await screen.findByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Revoke previous approval' }))
  await screen.findByRole('alert')
  expect(bodies[0]).toMatchObject({ decision: 'revoke', facet: 'application', expected_revision: 1 })
  expect(screen.queryByRole('button', { name: 'Retry same review' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  expect(await screen.findByRole('checkbox')).not.toBeChecked()
})

it('aborts an in-flight preview when leaving the screen', async () => {
  let signal: AbortSignal | null | undefined
  let resolve!: (value: Response) => void
  vi.stubGlobal('fetch', vi.fn((_path: string, init?: RequestInit) => {
    signal = init?.signal
    return new Promise<Response>(done => { resolve = done })
  }))
  const view = renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  view.unmount()
  expect(signal?.aborted).toBe(true)
  resolve(jsonResponse(preview))
  await Promise.resolve()
  expect(screen.queryByText('Explain selection bias')).not.toBeInTheDocument()
})


it('focuses saved feedback even when an animation frame precedes the React commit', async () => {
  vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => { callback(0); return 1 })
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => jsonResponse(init?.method === 'POST' ? { decision: 'revoke' } : { ...preview, current_review: { id: 'r1', revision: 1, decision: 'approve', facet: 'application', reviewed_at: '2026-10-12T10:00:00Z' } })))
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  fireEvent.click(await screen.findByRole('checkbox'))
  const revoke = screen.getByRole('button', { name: 'Revoke previous approval' })
  revoke.focus()
  fireEvent.click(revoke)
  expect(await screen.findByText('Review revoked. Your review history and past answers are kept.')).toHaveFocus()
})


it('keeps focus chosen by the learner while a review is saving', async () => {
  let resolve!: (value: Response) => void
  vi.stubGlobal('fetch', vi.fn((_path: string, init?: RequestInit) => init?.method === 'POST'
    ? new Promise<Response>(done => { resolve = done }) : Promise.resolve(jsonResponse(preview))))
  renderApp(<TaskReview />, { route: '/task-review?assessment=a1' })
  fireEvent.click(screen.getByRole('button', { name: 'Show task and rubric' }))
  fireEvent.click(await screen.findByRole('checkbox'))
  const approve = screen.getByRole('button', { name: 'Approve this task review' })
  approve.focus()
  fireEvent.click(approve)
  const back = screen.getByRole('link', { name: 'Back to Progress' })
  back.focus()
  resolve(jsonResponse({ decision: 'approve' }))
  await screen.findByText('Task review saved. This does not change your grades or confirm understanding.')
  expect(back).toHaveFocus()
})
