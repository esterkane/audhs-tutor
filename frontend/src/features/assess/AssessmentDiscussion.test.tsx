import { fireEvent, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { renderApp } from '../../test/utils'
import { AssessmentDiscussion } from './AssessmentDiscussion'

const unmount = vi.fn()
vi.mock('../programs/AnswerFollowup', async () => {
  const { useEffect } = await import('react')
  return {
    AnswerFollowup: ({
      answerId,
      expectedSessionId,
      active,
    }: {
      answerId: string
      expectedSessionId: string
      active: boolean
    }) => {
      useEffect(() => () => unmount(), [])
      return (
        <div data-active={String(active)}>
          Discussion {answerId} in {expectedSessionId}
        </div>
      )
    },
  }
})
it('opens explicitly with immutable parent and deactivates without discarding mounted reply state', async () => {
  const view = renderApp(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  expect(screen.queryByText('Discussion saved in original')).not.toBeInTheDocument()
  const details = screen.getByText('Discuss this feedback').closest('details')!
  details.open = true
  fireEvent(details, new Event('toggle'))
  expect(await screen.findByText('Discussion saved in original')).toBeVisible()
  view.rerender(<AssessmentDiscussion answerId="saved" sessionId="original" active={false} />)
  expect(screen.getByText('Discussion saved in original')).toHaveAttribute('data-active', 'false')
  expect(unmount).not.toHaveBeenCalled()
  view.rerender(<AssessmentDiscussion answerId="saved" sessionId="original" active />)
  expect(screen.getByText('Discussion saved in original')).toBeVisible()
  details.open = false
  fireEvent(details, new Event('toggle'))
  await waitFor(() =>
    expect(screen.getByText('Discussion saved in original')).toHaveAttribute('data-active', 'false'),
  )
  expect(unmount).not.toHaveBeenCalled()
})
it('does not fabricate a discussion parent when history was not saved', () => {
  renderApp(<AssessmentDiscussion answerId={null} sessionId="original" active />)
  expect(screen.queryByText('Discuss this feedback')).not.toBeInTheDocument()
})
