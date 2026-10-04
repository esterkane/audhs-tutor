import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { OriginalLesson } from './OriginalLesson'
import { apiFetch } from '../../lib/api'
vi.mock('../../lib/api', () => ({ apiFetch: vi.fn() }))
afterEach(() => vi.resetAllMocks())
const context = { version: 1 as const, kind: 'lesson' as const, label: 'Original lesson', session_id: 'session', skill_id: 'skill', block_index: 1, block_started_at: 'started' }
it('failed session reads offer retry without navigating or losing context', async () => {
  vi.mocked(apiFetch).mockRejectedValueOnce(new Error('offline'))
  const onOpen = vi.fn()
  render(<MemoryRouter><OriginalLesson context={context} onOpen={onOpen} /></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: /Open original lesson/ }))
  await screen.findByText(/Could not check your current session/)
  expect(onOpen).not.toHaveBeenCalled()
  expect(screen.queryByRole('link')).not.toBeInTheDocument()
  vi.mocked(apiFetch).mockResolvedValueOnce(null)
  fireEvent.click(screen.getByRole('button', { name: /Open original lesson/ }))
  await screen.findByRole('link', { name: 'Choose whether to return to this lesson' })
  expect(apiFetch).toHaveBeenCalledTimes(2)
})
it('closing while checking ignores a late response', async () => {
  let complete!: (value: unknown) => void
  vi.mocked(apiFetch).mockReturnValue(new Promise(resolve => { complete = resolve }))
  const onOpen = vi.fn()
  const view = render(<MemoryRouter><OriginalLesson context={context} onOpen={onOpen} /></MemoryRouter>)
  fireEvent.click(screen.getByRole('button', { name: /Open original lesson/ }))
  view.unmount()
  complete({ id: 'session', state: { skill_id: 'skill', block_index: 1, block_started_at: 'started', block_status: 'running' } })
  await waitFor(() => expect(onOpen).not.toHaveBeenCalled())
})
