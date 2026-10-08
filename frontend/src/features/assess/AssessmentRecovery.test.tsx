import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { AssessmentRecovery } from './AssessmentRecovery'
import type { useAssessmentSubmission } from './useAssessmentSubmission'

type Recovery = ReturnType<typeof useAssessmentSubmission>['recovery']
function recovery(): Recovery {
  return {
    pending: {
      version: 1,
      id: 'original',
      endpoint: '/api/assess/attempt',
      body: { session_id: 'session', assessment_id: 'item', answer: 'My explanation', hint_count: 0 },
      question: 'Original question',
      rejectedContent: true,
    },
    previousAnswer: null,
    previousAnswers: [],
    dismissPrevious: vi.fn(),
    stale: true,
    error: '',
    lookup: null,
    checking: false,
    memoryOnly: false,
    storageError: false,
    check: vi.fn(),
    resend: vi.fn(),
    finish: vi.fn(),
    continuePrepared: vi.fn(),
    clear: vi.fn(),
    reload: vi.fn(),
    continueInMemory: vi.fn(),
  }
}
it('shows original work and clears rejected identity only after explicit successful refresh', async () => {
  const state = recovery()
  let finish!: () => void
  const onRefresh = vi.fn(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve
      }),
  )
  render(<AssessmentRecovery recovery={state} onRefresh={onRefresh} />)
  expect(screen.getByText('Original question')).toBeInTheDocument()
  expect(screen.getByText('My explanation')).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: 'Send the original answer' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Review updated question — keep my answer' }))
  expect(state.clear).not.toHaveBeenCalled()
  finish()
  await waitFor(() => expect(state.clear).toHaveBeenCalledOnce())
})
it('keeps recovery if refresh fails', async () => {
  const state = recovery()
  render(
    <AssessmentRecovery
      recovery={state}
      onRefresh={async () => {
        throw new Error('Source unavailable')
      }}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Review updated question — keep my answer' }))
  expect(await screen.findByText('Source unavailable')).toBeInTheDocument()
  expect(state.clear).not.toHaveBeenCalled()
})
it('aborts refresh on unmount and cannot clear its saved identity from a late response', async () => {
  const state = recovery()
  let finish!: () => void
  let signal!: AbortSignal
  const view = render(
    <AssessmentRecovery
      recovery={state}
      onRefresh={(received) => {
        signal = received
        return new Promise<void>((resolve) => {
          finish = resolve
        })
      }}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Review updated question — keep my answer' }))
  view.unmount()
  expect(signal.aborted).toBe(true)
  finish()
  await Promise.resolve()
  expect(state.clear).not.toHaveBeenCalled()
})

it('offers explicit saving of a staged grade without a new submission', () => {
  const state = recovery()
  state.stale = false
  state.lookup = {
    status: 'grade_ready',
    result: null,
    saved_grade: {
      criterion_results: [],
      confidence: 0.8,
      feedback: 'Preserved explanation',
      next_step: 'Try another example',
    },
  }
  render(<AssessmentRecovery recovery={state} />)
  expect(screen.getByText(/does not ask the tutor to grade again/)).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Saved feedback — progress not yet confirmed' })).toBeVisible()
  expect(screen.getByText('Preserved explanation')).toBeVisible()
  expect(state.finish).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Finish saving this result' }))
  expect(state.finish).toHaveBeenCalledOnce()
  expect(state.resend).not.toHaveBeenCalled()
  expect(state.clear).not.toHaveBeenCalled()
})


it('offers explicit continuation only for verified prepared work', () => {
  const state = recovery()
  state.stale = false
  state.lookup = { status: 'prepared_ready', result: null }
  state.error = 'Request interrupted; check its result.'
  render(<AssessmentRecovery recovery={state} />)
  expect(screen.getByText(/your current edits will not be sent/)).toBeVisible()
  expect(screen.queryByText(/If storage is blocked/)).not.toBeInTheDocument()
  expect(state.continuePrepared).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Continue saved submission' }))
  expect(state.continuePrepared).toHaveBeenCalledTimes(1)
})
