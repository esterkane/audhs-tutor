import { useComfort } from './comfortStore'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, expect, it, vi } from 'vitest'
import { BreakReminder, ComfortToggle } from './ComfortControls'
import { useGenerationActivity } from './generationActivity'
vi.mock('../preferences/api', () => ({ usePreferences: () => ({ data: { values: { 'ui.break_reminder': '15' } } }) }))
afterEach(() => { cleanup(); vi.useRealTimers(); useGenerationActivity.setState({ count: 0 }); useComfort.setState({ focus: false }); localStorage.clear() })
function advanceActive() {
  for (let i = 0; i < 16; i++) { fireEvent.keyDown(window, { key: 'ArrowDown' }); act(() => vi.advanceTimersByTime(60_000)) }
}
it('counts active time, pauses while idle and defers reminders until generation and editing finish', async () => {
  vi.useFakeTimers()
  render(<MemoryRouter initialEntries={['/curriculum']}><textarea aria-label="Research" /><button>Done writing</button><BreakReminder /></MemoryRouter>)
  act(() => vi.advanceTimersByTime(16 * 60_000))
  expect(screen.queryByLabelText('Gentle break reminder')).toBeNull()
  act(() => useGenerationActivity.setState({ count: 1 }))
  advanceActive()
  expect(screen.queryByLabelText('Gentle break reminder')).toBeNull()
  act(() => screen.getByLabelText('Research').focus())
  act(() => useGenerationActivity.setState({ count: 0 }))
  expect(screen.queryByLabelText('Gentle break reminder')).toBeNull()
  await act(async () => { screen.getByRole('button', { name: 'Done writing' }).focus(); await Promise.resolve() })
  expect(screen.getByLabelText('Gentle break reminder')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Keep learning' }))
  expect(screen.queryByLabelText('Gentle break reminder')).toBeNull()
})
it('never reminds on settings and preserves the explicit focus choice across remounts', () => {
  vi.useFakeTimers()
  const view = render(<MemoryRouter initialEntries={['/preferences']}><ComfortToggle /><BreakReminder /></MemoryRouter>)
  advanceActive()
  expect(screen.queryByLabelText('Gentle break reminder')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Focus mode' }))
  expect(JSON.parse(localStorage.getItem('audhs-comfort')!).state.focus).toBe(true)
  view.unmount()
  render(<ComfortToggle />)
  expect(screen.getByRole('button', { name: 'Exit focus mode' })).toHaveAttribute('aria-pressed', 'true')
})
