import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AlongsideMode } from './AlongsideMode'

vi.mock('../../routes/Together', () => ({ Together: () => <p>Quiet panel</p> }))
afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear() })
function toggle(container: HTMLElement, open: boolean) {
  const details = container.querySelector('details')!
  details.open = open
  fireEvent(details, new Event('toggle'))
}

it('recovers the chosen panel only for the matching session and persists closing', () => {
  const first = render(<AlongsideMode sessionId="one" />)
  toggle(first.container, true)
  expect(screen.getByText('Quiet panel')).toBeVisible()
  first.unmount()
  const next = render(<AlongsideMode sessionId="one" />)
  expect(screen.getByText('Quiet panel')).toBeVisible()
  next.rerender(<AlongsideMode sessionId="two" />)
  expect(screen.queryByText('Quiet panel')).toBeNull()
  next.rerender(<AlongsideMode sessionId="one" />)
  expect(screen.getByText('Quiet panel')).toBeVisible()
  toggle(next.container, false)
  next.unmount()
  render(<AlongsideMode sessionId="one" />)
  expect(screen.queryByText('Quiet panel')).toBeNull()
})

it('keeps the panel usable and reports storage failure', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('denied') })
  const view = render(<AlongsideMode sessionId="one" />)
  toggle(view.container, true)
  expect(screen.getByText('Quiet panel')).toBeVisible()
  expect(screen.getByRole('status')).toHaveTextContent('cannot remember')
  toggle(view.container, false)
  expect(screen.queryByText('Quiet panel')).toBeNull()
})

it('does not open from malformed or unsupported saved state', () => {
  sessionStorage.setItem('session:alongside:v1', '{bad')
  const first = render(<AlongsideMode sessionId="one" />)
  expect(screen.queryByText('Quiet panel')).toBeNull()
  expect(screen.getByRole('status')).toBeVisible()
  first.unmount()
  sessionStorage.setItem('session:alongside:v1', JSON.stringify({ version: 9, sessionId: 'one', open: true }))
  render(<AlongsideMode sessionId="one" />)
  expect(screen.queryByText('Quiet panel')).toBeNull()
})
