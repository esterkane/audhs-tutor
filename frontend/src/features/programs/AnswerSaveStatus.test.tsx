import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { apiFetch } from '../../lib/api'
import { AnswerSaveStatus } from './AnswerSaveStatus'
vi.mock('../../lib/api', () => ({ apiFetch: vi.fn() }))
afterEach(() => { vi.resetAllMocks(); vi.useRealTimers() })

it('retries only the signed save and links the confirmed answer', async () => {
  vi.mocked(apiFetch).mockResolvedValue({ answer_id: 'saved' })
  const saved = vi.fn()
  renderApp(<AnswerSaveStatus error="Save failed" receipt="signed-receipt" text="Original answer" onSaved={saved} />)
  expect(apiFetch).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  const link = await screen.findByRole('link', { name: 'Open saved answer' })
  expect(link).toHaveAttribute('href', '/answers/saved')
  expect(apiFetch).toHaveBeenCalledTimes(1)
  expect(apiFetch).toHaveBeenCalledWith('/api/answers/recover-save', expect.objectContaining({
    method: 'POST', body: JSON.stringify({ receipt: 'signed-receipt' }),
  }))
  expect(saved).toHaveBeenCalledWith('saved')
})

it('keeps expired receipts copyable without regenerating', async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error('Receipt expired'))
  renderApp(<AnswerSaveStatus error="Save failed" receipt="expired" text="Original" />)
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  await screen.findByText('Receipt expired')
  expect(screen.getByRole('button', { name: 'Save a text copy' })).toBeEnabled()
  expect(screen.getByRole('button', { name: 'Retry saving' })).toBeEnabled()
})

it('ignores a completion after unmount', async () => {
  let finish!: (value: unknown) => void
  vi.mocked(apiFetch).mockImplementation(() => new Promise((resolve) => { finish = resolve }))
  const saved = vi.fn()
  const view = renderApp(<AnswerSaveStatus error="Save failed" receipt="receipt" text="Original" onSaved={saved} />)
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  view.unmount()
  await act(async () => finish({ answer_id: 'late' }))
  expect(saved).not.toHaveBeenCalled()
})

it('times out without losing the recovery action', async () => {
  vi.useFakeTimers()
  vi.mocked(apiFetch).mockImplementation(() => new Promise(() => {}))
  renderApp(<AnswerSaveStatus error="Save failed" receipt="receipt" text="Original" />)
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  await act(async () => { await vi.advanceTimersByTimeAsync(15000) })
  expect(screen.getByText(/Saving timed out/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Retry saving' })).toBeEnabled()
  vi.useRealTimers()
  await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))
})
