import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { StudyTutor } from './StudyTutor'
import { askTutor } from '../playground/api'
import { useCurrentSession } from '../session/api'
vi.mock('../playground/api', () => ({ askTutor: vi.fn() }))
vi.mock('../session/api', () => ({ useCurrentSession: vi.fn() }))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: ({ text }: { text: string }) => <button data-spoken-text={text}>Listen to explanation</button> }))
vi.mock('../voice/DictationButton', () => ({ DictationButton: () => <button type="button">Dictate</button> }))
const reply = {
  reused: false,
  text: 'Keep held-out data separate.',
  model: 'local',
  route: 'local',
  turn_id: 'turn',
  source_note: 'Guidance only',
}
function active() {
  vi.mocked(useCurrentSession).mockReturnValue({
    data: { id: 's' },
    isPending: false,
    isError: false,
  } as ReturnType<typeof useCurrentSession>)
}
afterEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
  localStorage.clear()
  sessionStorage.clear()
})
it('requires an explicit existing session', () => {
  vi.mocked(useCurrentSession).mockReturnValue({ data: null, isPending: false, isError: false } as ReturnType<
    typeof useCurrentSession
  >)
  renderApp(<StudyTutor context="Data split" />)
  expect(screen.getByRole('link', { name: 'Start or resume a session from Home' })).toHaveAttribute(
    'href',
    '/',
  )
  expect(askTutor).not.toHaveBeenCalled()
})
it('sends explicit bounded context, answer and opt-in Socratic intent', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  renderApp(<StudyTutor context={'A'.repeat(1200)} code={'B'.repeat(18000)} answer={'C'.repeat(5000)} />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask me a Socratic question' }))
  await screen.findByText(reply.text)
  expect(askTutor).toHaveBeenCalledWith(
    expect.objectContaining({
      session_id: 's',
      exercise: 'A'.repeat(1000),
      code: 'B'.repeat(16000),
      output: '',
      learner_answer: null,
      question: expect.stringContaining('explicitly choose Socratic'),
      questioning_style: 'socratic',
    }),
    expect.any(AbortSignal),
    expect.any(String),
  )
  expect(screen.getByText(/not a verified grade/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toBeVisible()
})
it('retains a failed message, clears it only on success, and carries conversation history', async () => {
  active()
  vi.mocked(askTutor).mockRejectedValueOnce(new Error('Offline')).mockResolvedValue(reply)
  renderApp(<StudyTutor context="Splitting data" />)
  const input = screen.getByLabelText('Your tutor message or response')
  fireEvent.change(input, { target: { value: 'Why split?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  await screen.findByRole('alert')
  expect(input).toHaveValue('Why split?')
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  await waitFor(() => expect(input).toHaveValue(''))
  fireEvent.change(input, { target: { value: 'And then?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  expect(vi.mocked(askTutor).mock.calls[2][0].history).toEqual([
    { role: 'user', text: 'Why split?' },
    { role: 'assistant', text: reply.text },
  ])
})
it('ignores a late response after Stop and when the topic changes', async () => {
  active()
  let resolve!: (value: typeof reply) => void
  vi.mocked(askTutor).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  const view = renderApp(<StudyTutor context="Topic A" />)
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop tutor response' }))
  resolve(reply)
  await waitFor(() => expect(screen.queryByText(reply.text)).toBeNull())
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  view.rerender(<StudyTutor context="Topic B" />)
  resolve(reply)
  await waitFor(() => expect(screen.queryByText(reply.text)).toBeNull())
})

it('restores an unsent message and conversation when returning to the same context', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  const view = renderApp(<StudyTutor context="Cell A" />)
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  await screen.findByText(reply.text)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), {
    target: { value: 'My unfinished response' },
  })
  view.rerender(<StudyTutor context="Cell B" />)
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('')
  view.rerender(<StudyTutor context="Cell A" />)
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('My unfinished response')
  expect(screen.getByText(reply.text)).toBeVisible()
})
it('cancels a request after answer changes and marks previous feedback stale', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValueOnce(reply)
  const view = renderApp(<StudyTutor context="Cell A" answer="First" />)
  fireEvent.click(screen.getByRole('button', { name: 'Review my answer' }))
  await screen.findByText(reply.text)
  let resolve!: (value: typeof reply) => void
  vi.mocked(askTutor).mockImplementation(
    () =>
      new Promise((r) => {
        resolve = r
      }),
  )
  fireEvent.click(screen.getByRole('button', { name: 'Review my answer' }))
  const signal = vi.mocked(askTutor).mock.calls[1][1]
  view.rerender(<StudyTutor context="Cell A" answer="Changed" />)
  expect(signal.aborted).toBe(true)
  resolve({ ...reply, text: 'Obsolete completion' })
  await waitFor(() => expect(screen.queryByText('Obsolete completion')).toBeNull())
  expect(screen.getByText(/Earlier feedback/)).toBeVisible()
})
it('labels actual output separately and reports storage failures without losing drafts', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  const store = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Quota')
  })
  renderApp(<StudyTutor context="Run" answer="My prediction" output="42" />)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), { target: { value: 'Keep me' } })
  expect(screen.getByText(/could not be saved/)).toBeVisible()
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('Keep me')
  fireEvent.click(screen.getByRole('button', { name: 'Review my answer' }))
  await screen.findByText(reply.text)
  expect(vi.mocked(askTutor).mock.calls[0][0].output).toBe('42')
  store.mockRestore()
})

it('keeps identical text in different notebook identities independent', () => {
  active()
  const view = renderApp(<StudyTutor context="Same instructions" identity="book-a:cell-1" />)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), {
    target: { value: 'Question A' },
  })
  view.rerender(<StudyTutor context="Same instructions" identity="book-b:cell-1" />)
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('')
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), {
    target: { value: 'Question B' },
  })
  view.rerender(<StudyTutor context="Same instructions" identity="book-a:cell-1" />)
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('Question A')
})

it('checks an answer explicitly against the selected question and offers spoken feedback', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  renderApp(
    <StudyTutor
      reviewOnly
      identity="question-1"
      context="Question: Why? Criteria: Mention selection bias."
      answer="Some groups lose more rows."
    />,
  )
  expect(askTutor).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: 'Explain this step' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(reply.text)
  expect(askTutor).toHaveBeenCalledWith(
    expect.objectContaining({
      exercise: 'Question: Why? Criteria: Mention selection bias.',
      question: expect.stringContaining('What needs revision'),
      learner_answer: 'Some groups lose more rows.',
      output: '',
    }),
    expect.any(AbortSignal),
    expect.any(String),
  )
})

it('guides a Socratic answer, preserves earlier messages, and can return to explanation', async () => {
  active()
  vi.mocked(askTutor)
    .mockResolvedValueOnce({ ...reply, text: 'Which group loses more rows?' })
    .mockResolvedValueOnce({ ...reply, text: 'Group B loses more. What changes in its representation?' })
    .mockResolvedValueOnce({ ...reply, text: 'Here is a direct explanation.' })
  renderApp(<StudyTutor context="Compare groups after cleaning." targetLabel="Step 1: data cleaning" />)
  expect(screen.getByText('Discussing: Step 1: data cleaning')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Ask me a Socratic question' }))
  await screen.findByText('Which group loses more rows?')
  const answer = screen.getByLabelText('Your answer to the tutor’s question')
  fireEvent.change(answer, { target: { value: 'Group B loses more rows.' } })
  fireEvent.click(screen.getByRole('button', { name: 'Discuss my answer' }))
  await screen.findByText('Group B loses more. What changes in its representation?')
  const sent = vi.mocked(askTutor).mock.calls[1][0]
  expect(sent.questioning_style).toBe('socratic')
  expect(sent.learner_answer).toBe('Group B loses more rows.')
  expect(sent.question).toContain('Group B loses more rows.')
  expect(sent.question).toContain('Give direct feedback on my answer first')
  expect(sent.history?.at(-1)?.text).toBe('Which group loses more rows?')
  fireEvent.click(screen.getByText('Earlier messages (2)'))
  expect(screen.getByText('Which group loses more rows?')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Explain instead' }))
  await screen.findByText('Here is a direct explanation.')
  expect(screen.getByLabelText('Your tutor message or response')).toBeVisible()
  expect(vi.mocked(askTutor).mock.calls[2][0].question).toContain('Switch back to direct explanation')
  expect(vi.mocked(askTutor).mock.calls[2][0].questioning_style).toBe('explicit')
})

it('allows follow-up questions after answer checking and keeps earlier feedback after edits', async () => {
  active()
  vi.mocked(askTutor)
    .mockResolvedValueOnce(reply)
    .mockResolvedValueOnce({ ...reply, text: 'The rule affects group sizes differently.' })
  const view = renderApp(
    <StudyTutor reviewOnly context="Question: Why?" identity="review" answer="My answer" />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(reply.text)
  fireEvent.change(screen.getByLabelText('Ask about this feedback'), {
    target: { value: 'Why does the rule matter?' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await screen.findByText('The rule affects group sizes differently.')
  expect(vi.mocked(askTutor).mock.calls[1][0].history?.at(-1)?.text).toBe(reply.text)
  view.rerender(<StudyTutor reviewOnly context="Question: Why?" identity="review" answer="Revised answer" />)
  fireEvent.click(screen.getByText('Earlier messages (2)'))
  expect(screen.getByText(reply.text)).toBeVisible()
})

it('adapts current feedback with history and preserves drafts, but rejects stale work', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  const view = renderApp(<StudyTutor context="Compare retention" identity="step" answer="First" />)
  expect(screen.queryByRole('button', { name: 'Shorter' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Review my answer' }))
  await screen.findByText(reply.text)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), {
    target: { value: 'Keep draft' },
  })
  for (const label of ['Shorter', 'Smaller steps', 'Show an example']) {
    fireEvent.click(screen.getByRole('button', { name: label }))
    await waitFor(() => expect(screen.getByRole('button', { name: label })).toBeEnabled())
    const request = vi.mocked(askTutor).mock.lastCall![0]
    expect(request.exercise).toBe('Compare retention')
    expect(request.history?.at(-1)?.text).toBe(reply.text)
    expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('Keep draft')
  }
  expect(vi.mocked(askTutor).mock.lastCall![0].question).toContain('illustrative')
  view.rerender(<StudyTutor context="Compare retention" identity="step" answer="Edited" />)
  expect(screen.queryByRole('button', { name: 'Shorter' })).toBeNull()
  expect(screen.getByText(/Earlier feedback/)).toBeVisible()
})

it('requires explicit explanation switch before adapting a Socratic question', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  renderApp(<StudyTutor context="Compare retention" />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask me a Socratic question' }))
  await screen.findByText(reply.text)
  expect(screen.queryByRole('button', { name: 'Shorter' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Explain instead' }))
  await screen.findByRole('button', { name: 'Shorter' })
})

it('shows elapsed waiting quietly and announces only the accepted completion', async () => {
  active()
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'performance'] })
  const completions: ((value: typeof reply) => void)[] = []
  vi.mocked(askTutor).mockImplementation(() => new Promise((resolve) => completions.push(resolve)))
  const view = renderApp(<StudyTutor context="Retention" identity="wait" />)
  const status = screen.getByRole('status', { name: 'Tutor response status' })
  expect(status).toBeEmptyDOMElement()
  const input = screen.getByLabelText('Your tutor message or response')
  fireEvent.change(input, { target: { value: 'Keep this draft' } })
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  expect(status).toHaveTextContent('Tutor is preparing a response')
  await act(async () => vi.advanceTimersByTime(4000))
  expect(screen.getByText(/Waiting 4 seconds/)).toHaveAttribute('aria-live', 'off')
  expect(status).not.toHaveTextContent('seconds')
  fireEvent.click(screen.getByRole('button', { name: 'Stop tutor response' }))
  expect(status).toBeEmptyDOMElement()
  expect(screen.queryByText(/Waiting 4 seconds/)).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  expect(screen.getByText(/Waiting 0 seconds/)).toBeVisible()
  await act(async () => completions[0]({ ...reply, text: 'Discard this stale response' }))
  expect(screen.queryByText('Discard this stale response')).toBeNull()
  expect(status).toHaveTextContent('Tutor is preparing a response')
  await act(async () => completions[1](reply))
  expect(status).toHaveTextContent('Tutor response ready.')
  expect(input).toHaveValue('Keep this draft')
  expect(screen.queryByText(/Waiting \d+ seconds/)).toBeNull()
  view.unmount()
  renderApp(<StudyTutor context="Retention" identity="wait" />)
  expect(screen.getByRole('status', { name: 'Tutor response status' })).toBeEmptyDOMElement()
  expect(screen.getByText(reply.text)).toBeVisible()
})

it('times out waiting without announcing a late completion or losing the draft', async () => {
  active()
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval', 'performance'] })
  let finish!: (value: typeof reply) => void
  vi.mocked(askTutor).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve
      }),
  )
  renderApp(<StudyTutor context="Retention" />)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), {
    target: { value: 'My question' },
  })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  await act(async () => vi.advanceTimersByTime(90000))
  expect(screen.getByRole('alert')).toHaveTextContent('took too long')
  expect(vi.mocked(askTutor).mock.lastCall![1].aborted).toBe(true)
  await act(async () => finish(reply))
  expect(screen.getByRole('status', { name: 'Tutor response status' })).toBeEmptyDOMElement()
  expect(screen.getByLabelText('Your tutor message or response')).toHaveValue('My question')
})

it('does not steal focus when the learner moves to another control before the completion frame', async () => {
  active()
  const frames: FrameRequestCallback[] = []
  const schedule = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
    frames.push(callback)
    return frames.length
  })
  try {
    vi.mocked(askTutor).mockResolvedValue(reply)
    renderApp(<StudyTutor context="Retention" />)
    const explain = screen.getByRole('button', { name: 'Explain this step' })
    explain.focus()
    fireEvent.click(explain)
    await screen.findByText(reply.text)
    const shorter = screen.getByRole('button', { name: 'Shorter' })
    shorter.focus()
    act(() => frames.forEach((frame) => frame(0)))
    expect(shorter).toHaveFocus()
  } finally {
    schedule.mockRestore()
  }
})

it('distinguishes a durable saved reply from a delivered reply whose save failed', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValueOnce({ ...reply, answer_id: 'answer-1' })
  renderApp(<StudyTutor context="Data split" />)
  fireEvent.click(screen.getByRole('button', { name: 'Explain this step' }))
  await screen.findByText('Saved to your local answer history.')
  vi.mocked(askTutor).mockResolvedValueOnce({
    ...reply,
    answer_id: null,
    save_error: 'This answer could not be saved to the database. Keep a copy before leaving.',
  })
  fireEvent.click(screen.getByRole('button', { name: 'Shorter' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be saved')
  expect(screen.getAllByText(reply.text)).toHaveLength(2)
  expect(screen.queryByText('Saved to your local answer history.')).not.toBeInTheDocument()
})
it('shows links to the prior answers used as historical context', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue({ ...reply, memory_answers: ['previous-one'] })
  renderApp(<StudyTutor context="Groups" />)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), { target: { value: 'Why compare?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  expect(await screen.findByRole('link', { name: 'Open previous answer' })).toHaveAttribute('href', '/answers/previous-one')
})
it('opts into saved reuse explicitly and labels the original dated response', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue({ ...reply, reused: true, saved_at: '2026-10-01T09:00:00Z', answer_id: 'old' })
  renderApp(<StudyTutor context="Groups" />)
  const reuse = screen.getByRole('checkbox', { name: /Use a saved answer/ })
  expect(reuse).not.toBeChecked()
  fireEvent.click(reuse)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), { target: { value: 'Why compare?' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  await screen.findByText(/Saved answer from 2026-10-01/)
  expect(askTutor).toHaveBeenLastCalledWith(expect.objectContaining({ prefer_saved: true }), expect.any(AbortSignal), expect.any(String))
  fireEvent.click(reuse)
  fireEvent.change(screen.getByLabelText('Your tutor message or response'), { target: { value: 'Explain again' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send to tutor' }))
  await waitFor(() => expect(askTutor).toHaveBeenLastCalledWith(expect.objectContaining({ prefer_saved: false }), expect.any(AbortSignal), expect.any(String)))
})


it('sends the full task answer separately from output and refuses silent truncation', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  const exact = '  ' + 'A'.repeat(7900) + ' end  '
  const view = renderApp(<StudyTutor reviewOnly context="Check retention" answer={exact} output="run result" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(reply.text)
  expect(vi.mocked(askTutor).mock.calls[0][0]).toMatchObject({learner_answer: exact, output: 'run result'})
  view.rerender(<StudyTutor reviewOnly context="Check retention" answer={'B'.repeat(8001)} output="run result" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('8,000 characters')
  expect(askTutor).toHaveBeenCalledTimes(1)
  view.rerender(<StudyTutor reviewOnly context="Check retention" answer="revised" output="run result" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await waitFor(() => expect(askTutor).toHaveBeenCalledTimes(2))
  expect(vi.mocked(askTutor).mock.calls[1][0]).toMatchObject({learner_answer: 'revised', history: []})
})

it('does not submit an unsent Socratic response when requesting a hint', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  renderApp(<StudyTutor context="Retention" answer="older task answer" />)
  fireEvent.click(screen.getByRole('button', { name: 'Ask me a Socratic question' }))
  await screen.findByText(reply.text)
  const input = screen.getByLabelText('Your answer to the tutor’s question')
  fireEvent.change(input, {target: {value: 'unsent answer'}})
  fireEvent.click(screen.getByRole('button', { name: /hint/i }))
  await waitFor(() => expect(askTutor).toHaveBeenCalledTimes(2))
  expect(vi.mocked(askTutor).mock.calls[1][0].learner_answer).toBeNull()
  expect(input).toHaveValue('unsent answer')
})


it('reads the same local arithmetic disclosure as the displayed tutor reply', async () => {
  active()
  const text = 'Local arithmetic check (not a grade):\n\n30/50 = 0.9 does not hold exactly. Left side: 3/5 (0.6).\n\nTutor explanation (model-generated; may contain errors):\n\nYour calculation is correct.'
  vi.mocked(askTutor).mockResolvedValue({...reply, text})
  renderApp(<StudyTutor reviewOnly context="Retention" answer="30/50 = 0.9" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  expect(await screen.findByText('Local arithmetic check (not a grade):')).toBeVisible()
  expect(screen.getByText(/does not hold exactly/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toHaveAttribute('data-spoken-text', text)
})
it('discloses the answer-feedback provider and sends only an explicit check action to it', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  renderApp(<StudyTutor context="30 of 50 rows remain" answer="30/50 = 0.9" reviewOnly />)
  expect(screen.getByText(/OpenAI by default/)).toBeVisible()
  expect(askTutor).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(reply.text)
  expect(vi.mocked(askTutor).mock.calls[0][0]).toMatchObject({
    intent: 'check_answer', learner_answer: '30/50 = 0.9', questioning_style: 'explicit',
  })
  expect(screen.getByRole('button', { name: 'Listen to explanation' })).toHaveAttribute('data-spoken-text', reply.text)
  fireEvent.change(screen.getByLabelText('Ask about this feedback'), { target: { value: 'Explain the denominator' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send follow-up' }))
  await waitFor(() => expect(askTutor).toHaveBeenCalledTimes(2))
  expect(vi.mocked(askTutor).mock.calls[1][0].intent).toBe('chat')
})

it('keeps the full selected question for checks and refuses oversized material without a call', async () => {
  active()
  vi.mocked(askTutor).mockResolvedValue(reply)
  const context = 'Context '.repeat(180) + 'Important question at the end'
  const view = renderApp(<StudyTutor context={context} answer="My answer" reviewOnly />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(reply.text)
  expect(vi.mocked(askTutor).mock.calls[0][0].exercise).toBe(context)
  view.rerender(<StudyTutor context={'x'.repeat(8001)} answer="My answer" reviewOnly />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(/no question or criteria are omitted/)
  expect(askTutor).toHaveBeenCalledTimes(1)
})

it('recovers an exact request after reload without replacing a newly edited answer', async () => {
  active()
  vi.mocked(askTutor).mockRejectedValueOnce(new Error('Response lost')).mockResolvedValue(reply)
  const first = renderApp(<StudyTutor reviewOnly identity="step" context="Original material" answer="Original answer" />)
  fireEvent.click(screen.getByRole('button', { name: 'Check my answer' }))
  await screen.findByText(/Response lost/)
  const original = vi.mocked(askTutor).mock.calls[0]
  first.unmount()
  renderApp(<StudyTutor reviewOnly identity="step" context="Original material" answer="Edited answer" />)
  expect(screen.getByRole('button', { name: 'Retry previous request' })).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Retry previous request' }))
  await screen.findByText(reply.text)
  expect(vi.mocked(askTutor).mock.calls[1][0]).toEqual(original[0])
  expect(vi.mocked(askTutor).mock.calls[1][2]).toEqual(original[2])
  expect(screen.queryByRole('button', { name: 'Retry previous request' })).not.toBeInTheDocument()
})
