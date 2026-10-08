import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { jsonResponse, renderApp } from '../../test/utils'
import { QuestionPractice } from './QuestionPractice'

const preview = { status: { assessment_id: 'q1', state: 'active', revision: 0, reason: '' }, skill_title: 'Synthetic', question: 'Why?', affected_reviews: 2 }
afterEach(() => vi.unstubAllGlobals())

it('loads on request, previews impact and requires an explicit action', async () => {
  const changed = vi.fn()
  const fetcher = vi.fn(async (_path, init?: RequestInit) => jsonResponse(init?.method === 'POST' ? { ...preview.status, state: 'suspended', revision: 1 } : preview))
  vi.stubGlobal('fetch', fetcher)
  renderApp(<QuestionPractice assessmentId="q1" onChanged={changed} />)
  expect(fetcher).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
  await screen.findByText(/2 existing review card/)
  expect(fetcher).toHaveBeenCalledTimes(1)
  fireEvent.change(screen.getByLabelText('Reason (optional)'), { target: { value: 'Wrong context' } })
  fireEvent.click(screen.getByRole('button', { name: 'Exclude this question' }))
  await screen.findByText(/Excluded from future practice/)
  expect(changed).toHaveBeenCalledWith('q1', expect.objectContaining({ state: 'suspended' }))
  const body = JSON.parse(String(fetcher.mock.calls[1][1]?.body))
  expect(body).toMatchObject({ action: 'suspend', expected_revision: 0, reason: 'Wrong context' })
  expect(body.request_id).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Restore this question' })).toBeEnabled()
})

it('retries an uncertain write with the identical request and blocks rapid duplicates', async () => {
  const writes: string[] = []
  let reject!: (e: Error) => void
  vi.stubGlobal('fetch', vi.fn(async (_path, init?: RequestInit) => {
    if (init?.method !== 'POST') return jsonResponse(preview)
    writes.push(String(init.body))
    if (writes.length === 1) return new Promise<Response>((_, no) => { reject = no })
    return jsonResponse({ ...preview.status, state: 'suspended', revision: 1 })
  }))
  renderApp(<QuestionPractice assessmentId="q1" />)
  fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
  const button = await screen.findByRole('button', { name: 'Exclude this question' })
  fireEvent.click(button)
  fireEvent.click(button)
  expect(writes).toHaveLength(1)
  reject(new Error('Connection lost'))
  fireEvent.click(await screen.findByRole('button', { name: 'Retry same action' }))
  await screen.findByText(/Excluded from future practice/)
  expect(writes).toHaveLength(2)
  expect(writes[1]).toBe(writes[0])
})

it('requires a fresh status after a version conflict', async () => {
  let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (_path, init?: RequestInit) => {
    if (init?.method === 'POST') return jsonResponse({ error: { code: 'question_state_conflict', message: 'Changed elsewhere' } }, 409)
    reads++
    return jsonResponse(reads === 1 ? preview : { ...preview, status: { ...preview.status, state: 'suspended', revision: 1 } })
  }))
  renderApp(<QuestionPractice assessmentId="q1" />)
  fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
  fireEvent.click(await screen.findByRole('button', { name: 'Exclude this question' }))
  await screen.findByText(/Changed elsewhere/)
  expect(screen.getByRole('button', { name: 'Exclude this question' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Reload question status' }))
  await waitFor(() => expect(screen.getByRole('button', { name: 'Restore this question' })).toBeEnabled())
})
