import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { StudyTutor } from './StudyTutor'
import { askTutor } from '../playground/api'
import { useCurrentSession } from '../session/api'
vi.mock('../playground/api', () => ({ askTutor: vi.fn() }))
vi.mock('../session/api', () => ({ useCurrentSession: vi.fn() }))
vi.mock('../voice/ReadAloud', () => ({ ReadAloud: () => <button>Listen to explanation</button> }))
vi.mock('../voice/DictationButton', () => ({ DictationButton: () => <button type="button">Dictate</button> }))
const reply = {
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
  vi.resetAllMocks()
  localStorage.clear()
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
      output: expect.stringContaining('Learner answer (not execution output):\n' + 'C'.repeat(1950)),
      question: expect.stringContaining('explicitly choose Socratic'),
    }),
    expect.any(AbortSignal),
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
  expect(vi.mocked(askTutor).mock.calls[0][0].output).toContain(
    'Actual run output (not verified by tutor):\n42',
  )
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
