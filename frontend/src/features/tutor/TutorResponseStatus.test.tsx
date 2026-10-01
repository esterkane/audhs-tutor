import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { TutorResponseStatus } from './TutorResponseStatus'

afterEach(() => vi.useRealTimers())
it('announces terminal states without timer ticks or calling partial output complete', () => {
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'performance'] })
  const view = render(<TutorResponseStatus status="idle" startedAt={null} />)
  const status = screen.getByRole('status', { name: 'Tutor response status' })
  expect(status).toBeEmptyDOMElement()
  view.rerender(<TutorResponseStatus status="streaming" startedAt={performance.now()} />)
  const waitingMessage = status.textContent
  act(() => vi.advanceTimersByTime(5000))
  expect(screen.getByText(/Waiting 5 seconds/)).toHaveAttribute('aria-live', 'off')
  expect(status.textContent).toBe(waitingMessage)
  view.rerender(<TutorResponseStatus status="partial" startedAt={0} />)
  expect(status).toHaveTextContent('Response interrupted')
  expect(status).not.toHaveTextContent('ready')
  expect(screen.queryByText(/Waiting 5 seconds/)).toBeNull()
  expect(vi.getTimerCount()).toBe(0)
  view.rerender(<TutorResponseStatus status="complete" startedAt={0} />)
  expect(status).toHaveTextContent('Tutor response ready.')
})
