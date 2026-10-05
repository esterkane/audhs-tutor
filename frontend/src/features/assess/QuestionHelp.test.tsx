import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { streamTurn, type StreamHandlers } from '../../lib/api'
import { QuestionHelp } from './QuestionHelp'

vi.mock('../../lib/api', async (original) => ({ ...await original<typeof import('../../lib/api')>(), streamTurn: vi.fn() }))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <button>Test reading audio</button> }))
afterEach(() => vi.clearAllMocks())

it('stops hidden help, ignores late tokens and retains received help on return', async () => {
  let handlers!: StreamHandlers
  let signal!: AbortSignal
  let finish!: () => void
  vi.mocked(streamTurn).mockImplementation((_request, h, abort) => {
    handlers = h
    signal = abort!
    return new Promise<void>((resolve) => { finish = resolve })
  })
  const props = { sessionId: 's', skillId: 'k', question: 'What is the value?', onHint: vi.fn() }
  const view = render(<QuestionHelp {...props} active />)
  fireEvent.click(screen.getByRole('button', { name: 'Give me a hint' }))
  act(() => handlers.onToken?.('Keep this useful hint.'))
  view.rerender(<QuestionHelp {...props} active={false} />)
  expect(signal.aborted).toBe(true)
  expect(screen.queryByRole('button', { name: 'Test reading audio' })).not.toBeInTheDocument()
  await act(async () => {
    handlers.onToken?.('Late text must not replace it.')
    finish()
  })
  view.rerender(<QuestionHelp {...props} active />)
  expect(screen.getByText('Keep this useful hint.')).toBeVisible()
  expect(screen.queryByText(/Late text/)).not.toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Test reading audio' })).toBeVisible()
  expect(streamTurn).toHaveBeenCalledTimes(1)
})
