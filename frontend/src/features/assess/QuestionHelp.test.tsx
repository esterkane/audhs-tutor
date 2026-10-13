import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { streamTurn, type StreamHandlers } from '../../lib/api'
import { QuestionHelp } from './QuestionHelp'

vi.mock('../../lib/api', async (original) => ({
  ...(await original<typeof import('../../lib/api')>()),
  streamTurn: vi.fn(),
}))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <button>Test reading audio</button> }))
afterEach(() => vi.clearAllMocks())

it('stops hidden help, ignores late tokens and retains received help on return', async () => {
  let handlers!: StreamHandlers
  let signal!: AbortSignal
  let finish!: () => void
  vi.mocked(streamTurn).mockImplementation((_request, h, abort) => {
    handlers = h
    signal = abort!
    return new Promise<void>((resolve) => {
      finish = resolve
    })
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

it('offers concept help after feedback without changing hint evidence or grading', async () => {
  const onHint = vi.fn()
  vi.mocked(streamTurn).mockImplementation(async (_request, handlers) => {
    handlers.onMeta?.({ turn_id: 'post-grade' } as Parameters<NonNullable<StreamHandlers['onMeta']>>[0])
    handlers.onToken?.('Compare the quantities in a similar example.')
  })
  render(<QuestionHelp afterAnswer sessionId="s" skillId="k" question="What is the value?" onHint={onHint} />)
  expect(streamTurn).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: 'Give me a hint' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: "I don't understand yet — explain the idea" }))
  expect(await screen.findByText('Compare the quantities in a similar example.')).toBeVisible()
  expect(streamTurn).toHaveBeenCalledWith(
    expect.objectContaining({
      session_id: 's',
      skill_id: 'k',
      action: 'explain',
      text: expect.stringContaining('What is the value?'),
    }),
    expect.any(Object),
    expect.any(AbortSignal),
    undefined,
  )
  expect(onHint).not.toHaveBeenCalled()
})

it.each([
  ['Show a hint', 'hint'],
  ['Explain the difficult part', 'explain'],
  ['Show another example', 'explain'],
  ['See full solution', 'full_solution'],
])('requests %s only deliberately and retains recorded feedback context', async (label, action) => {
  const onHint = vi.fn()
  vi.mocked(streamTurn).mockImplementation(async (_request, handlers) => {
    handlers.onMeta?.({ turn_id: 'help' } as Parameters<NonNullable<StreamHandlers['onMeta']>>[0])
    handlers.onToken?.('Requested help, separate from grading.')
  })
  render(<QuestionHelp afterAnswer assessmentAnswerId="saved-assessment" sessionId="s" skillId="k" question="Compare these quantities." onHint={onHint} />)
  expect(streamTurn).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: label }))
  expect(await screen.findByText('Requested help, separate from grading.')).toBeVisible()
  expect(streamTurn).toHaveBeenCalledWith(expect.objectContaining({
    action, assessment_answer_id: 'saved-assessment',
  }), expect.any(Object), expect.any(AbortSignal), undefined)
  expect(onHint).not.toHaveBeenCalled()
})

it('keeps contextual help disabled until the checked feedback has been saved', () => {
  render(<QuestionHelp afterAnswer assessmentAnswerId={null} sessionId="s" skillId="k" question="Question" />)
  expect(screen.getByRole('button', { name: 'See full solution' })).toBeDisabled()
  expect(screen.getByText(/Save your feedback using the retry control/)).toBeVisible()
  expect(streamTurn).not.toHaveBeenCalled()
})

it('ignores old hint completion after the question identity changes', async () => {
  let handlers!: StreamHandlers
  let signal!: AbortSignal
  let finish!: () => void
  vi.mocked(streamTurn).mockImplementation((_request, h, abort) => {
    handlers = h; signal = abort!
    return new Promise<void>(resolve => { finish = resolve })
  })
  const oldHint = vi.fn()
  const newHint = vi.fn()
  const view = render(<QuestionHelp key="same-item-version-one" sessionId="s" skillId="k" question="Old wording" onHint={oldHint} />)
  fireEvent.click(screen.getByRole('button', { name: 'Give me a hint' }))
  view.rerender(<QuestionHelp key="same-item-version-two" sessionId="s" skillId="k" question="New wording" onHint={newHint} />)
  expect(signal.aborted).toBe(true)
  await act(async () => {
    handlers.onMeta?.({ turn_id: 'old-hint' } as Parameters<NonNullable<StreamHandlers['onMeta']>>[0])
    handlers.onToken?.('Hint for old wording')
    finish()
  })
  expect(screen.queryByText('Hint for old wording')).not.toBeInTheDocument()
  expect(oldHint).not.toHaveBeenCalled()
  expect(newHint).not.toHaveBeenCalled()
})
