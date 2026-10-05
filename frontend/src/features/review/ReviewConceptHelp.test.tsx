import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { streamTurn, type StreamHandlers } from '../../lib/api'
import { ReviewConceptHelp } from './ReviewConceptHelp'

vi.mock('../../lib/api', async original => ({
  ...(await original<typeof import('../../lib/api')>()), streamTurn: vi.fn(),
}))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <button>Read help</button> }))
afterEach(() => vi.clearAllMocks())

it('opens without inference, retains help on collapse, and stops it when rating starts', async () => {
  let handlers!: StreamHandlers
  let signal!: AbortSignal
  let finish!: () => void
  vi.mocked(streamTurn).mockImplementation((_body, h, abort) => {
    handlers = h
    signal = abort!
    return new Promise<void>(resolve => { finish = resolve })
  })
  const props = { sessionId: 's', skillId: 'k', question: 'Why compare proportions?', active: true }
  const view = render(<ReviewConceptHelp {...props} />)
  const details = view.container.querySelector('details')!
  const toggle = async (open: boolean) => {
    await act(async () => { details.open = open; fireEvent(details, new Event('toggle')) })
  }
  await toggle(true)
  expect(streamTurn).not.toHaveBeenCalled()
  expect(screen.getByText(/does not record a review rating/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: "I don't understand yet — explain the idea" }))
  act(() => handlers.onToken?.('Keep this explanation.'))
  await toggle(false)
  expect(signal.aborted).toBe(true)
  await act(async () => { handlers.onToken?.('Stale text.'); finish() })
  await toggle(true)
  expect(screen.getByText('Keep this explanation.')).toBeVisible()
  expect(screen.queryByText(/Stale text/)).not.toBeInTheDocument()
  expect(streamTurn).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: "I don't understand yet — explain the idea" }))
  view.rerender(<ReviewConceptHelp {...props} active={false} />)
  await waitFor(() => expect(signal.aborted).toBe(true))
  expect(screen.getByRole('button', { name: "I don't understand yet — explain the idea" })).toBeDisabled()
  expect(screen.queryByRole('button', { name: 'Read help' })).not.toBeInTheDocument()
  await act(async () => { finish() })
})
