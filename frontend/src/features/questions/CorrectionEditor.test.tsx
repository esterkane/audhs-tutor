import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { CorrectionEditor } from './CorrectionEditor'

const candidate = { item: { question: 'Original question?', options: ['One', 'Two'], answer: 0, explanation: 'Reason', source_chunk_id: 'kept' }, rubric: null }
const original = { id: 'draft1', assessment_id: 'a1', revision: 1, status: 'draft', kind: 'mcq', updated_at: '2026-10-08',
  candidate, original_candidate: candidate, rationale: '', contains_reference_answers: true,
  review: { problems: [], content_changed: false, question_state_changed: false, source_status: 'unchanged', draft_status: 'draft', publication_available: false } }
beforeEach(() => sessionStorage.clear())
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks() })

it('reveals references only after explicit authoring entry and creates once', async () => {
  const writes: unknown[] = []
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path.endsWith('correction-source')) return jsonResponse({ assessment_id: 'a1', kind: 'mcq', candidate, question_revision: 0, content_version: 'ac1.' + 'a'.repeat(64) })
    if (init?.method === 'POST') { writes.push(JSON.parse(String(init.body))); return jsonResponse({ draft_id: 'draft1', revision: 1, status: 'draft' }) }
    return jsonResponse(original)
  })
  vi.stubGlobal('fetch', fetcher)
  renderApp(<CorrectionEditor />, { route: '/corrections?assessment=a1' })
  expect(fetcher).not.toHaveBeenCalled()
  const start = screen.getByRole('button', { name: 'Show reference answers and start a draft' })
  fireEvent.click(start); fireEvent.click(start)
  await screen.findByLabelText('Question wording')
  expect(writes).toHaveLength(1)
  expect(screen.getByLabelText('Correct option')).toHaveValue('0')
})

it('recovers a lost save response after remount without dropping newer local edits', async () => {
  let server = structuredClone(original)
  const writes: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === 'PUT') {
      writes.push(String(init.body))
      const body = JSON.parse(String(init.body))
      server = { ...server, revision: 2, candidate: body.candidate, rationale: body.rationale }
      throw new Error('Lost response after commit')
    }
    if (path.includes('correction-commands')) return jsonResponse({ draft_id: 'draft1', revision: 2, status: 'draft' })
    return jsonResponse(server)
  }))
  const first = renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  fireEvent.change(await screen.findByLabelText('Question wording'), { target: { value: 'Submitted edit?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save correction draft' }))
  await screen.findByText(/The result is uncertain/)
  fireEvent.change(screen.getByLabelText('Question wording'), { target: { value: 'Newer local edit?' } })
  first.unmount()
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  expect(await screen.findByLabelText('Question wording')).toHaveValue('Newer local edit?')
  fireEvent.click(screen.getByRole('button', { name: 'Check save status' }))
  await screen.findByText('Submitted version saved. Your newer edits are still unsaved.')
  expect(screen.getByLabelText('Question wording')).toHaveValue('Newer local edit?')
  expect(writes).toHaveLength(1)
  await waitFor(() => expect(screen.getByRole('button', { name: 'Save correction draft' })).toBeEnabled())
})

it('preserves option metadata and requires answer reselection after options change', async () => {
  let sent: Record<string, unknown> | null = null
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => {
    if (init?.method === 'PUT') { sent = JSON.parse(String(init.body)); return jsonResponse({ draft_id: 'draft1', revision: 2, status: 'draft' }) }
    return jsonResponse(original)
  }))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  fireEvent.change(await screen.findByLabelText('Options (one per line)'), { target: { value: 'Two\nOne' } })
  expect(screen.getByLabelText('Correct option')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Correct option'), { target: { value: '1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save correction draft' }))
  await waitFor(() => expect(sent).not.toBeNull())
  expect(sent).toMatchObject({ candidate: { item: { answer: 1, options: ['Two', 'One'], source_chunk_id: 'kept' } } })
})

it('retains dirty work on conflict and requires explicit comparison before rebase', async () => {
  let server = structuredClone(original)
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => {
    if (init?.method === 'PUT') { server = { ...server, revision: 2 }; return jsonResponse({ error: { code: 'correction_draft_conflict', message: 'Changed elsewhere' } }, 409) }
    return jsonResponse(server)
  }))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  fireEvent.change(await screen.findByLabelText('Question wording'), { target: { value: 'Keep my edits?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save correction draft' }))
  await screen.findByText('Changed elsewhere')
  fireEvent.click(screen.getByRole('button', { name: 'Compare with saved version' }))
  const rebase = await screen.findByRole('button', { name: 'Keep my edits against this saved version' })
  expect(screen.getByLabelText('Question wording')).toHaveValue('Keep my edits?')
  expect(screen.getByRole('button', { name: 'Save correction draft' })).toBeDisabled()
  fireEvent.click(rebase)
  expect(screen.getByRole('button', { name: 'Save correction draft' })).toBeEnabled()
})

it('does not send a new write when retry storage fails', async () => {
  const writes: unknown[] = []
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => { if (init?.method) writes.push(init); return jsonResponse(original) }))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  fireEvent.change(await screen.findByLabelText('Question wording'), { target: { value: 'Keep on screen?' } })
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Quota') })
  fireEvent.click(screen.getByRole('button', { name: 'Save correction draft' }))
  await screen.findByText(/Nothing new was sent/)
  expect(writes).toHaveLength(0)
  expect(screen.getByLabelText('Question wording')).toHaveValue('Keep on screen?')
})


it('keeps the pending command when a receipt belongs to another draft', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => init?.method === 'PUT'
    ? jsonResponse({ draft_id: 'other-draft', revision: 9, status: 'draft' }) : jsonResponse(original)))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  fireEvent.change(await screen.findByLabelText('Question wording'), { target: { value: 'Still unsaved?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save correction draft' }))
  await screen.findByText('The saved response does not match this draft. Retry details are kept.')
  expect(sessionStorage.getItem('correction-command:v1:draft:draft1')).toBeTruthy()
  expect(screen.getByLabelText('Question wording')).toHaveValue('Still unsaved?')
  expect(screen.getByRole('button', { name: 'Check save status' })).toBeEnabled()
})

it('does not send malformed recovered command bodies', async () => {
  sessionStorage.setItem('correction-command:v1:draft:draft1', JSON.stringify({ scope: 'draft:draft1',
    command: { action: 'save', body: { request_id: crypto.randomUUID(), expected_revision: 1 } } }))
  const writes: unknown[] = []
  vi.stubGlobal('fetch', vi.fn(async (_path: string, init?: RequestInit) => { if (init?.method) writes.push(init); return jsonResponse(original) }))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  await screen.findByText(/Retry details could not be read/)
  fireEvent.change(screen.getByLabelText('Question wording'), { target: { value: 'Keep local work?' } })
  expect(screen.getByRole('button', { name: 'Save correction draft' })).toBeDisabled()
  expect(writes).toHaveLength(0)
})

it('keeps a published correction read-only without calling it discarded', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ ...original, status: 'published', review: { ...original.review, draft_status: 'published' } })))
  renderApp(<CorrectionEditor />, { route: '/corrections?draft=draft1' })
  expect(await screen.findByText('This correction was published. Its draft is retained for reference.')).toBeVisible()
  expect(screen.getByLabelText('Question wording')).toBeDisabled()
  expect(screen.getByRole('button', { name: 'Save correction draft' })).toBeDisabled()
})
