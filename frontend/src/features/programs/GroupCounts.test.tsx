import { fireEvent, render, screen, within, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { GroupCounts } from './GroupCounts'

beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})
function enter(a: string, b: string, c: string, d: string) {
  for (const [label, value] of [
    ['Group 1 before count', a],
    ['Group 1 after count', b],
    ['Group 2 before count', c],
    ['Group 2 after count', d],
  ])
    fireEvent.change(screen.getByLabelText(label), { target: { value } })
  fireEvent.click(screen.getByRole('button', { name: 'Compare counts' }))
}
it('compares retention, removal and representation using their own denominators', () => {
  render(<GroupCounts storageKey="test" />)
  enter('80', '72', '20', '8')
  const a = within(screen.getByRole('row', { name: /^A / }))
  const b = within(screen.getByRole('row', { name: /^B / }))
  expect(a.getAllByText('72/80 = 90.00%')[0]).toBeVisible()
  expect(b.getByText('8/20 = 40.00%')).toBeVisible()
  expect(b.getByText('20/100 = 20.00%')).toBeVisible()
  expect(b.getByText('8/80 = 10.00%')).toBeVisible()
  expect(b.getByText('-10.00 percentage points')).toBeVisible()
})
it('keeps removed counts distinct from proportional removal', () => {
  render(<GroupCounts storageKey="test" />)
  enter('200', '160', '40', '20')
  expect(screen.getByText('40/200 = 20.00%')).toBeVisible()
  expect(screen.getAllByText('20/40 = 50.00%').length).toBeGreaterThan(0)
})
it('zero denominators are undefined rather than zero percent', () => {
  render(<GroupCounts storageKey="test" />)
  enter('0', '0', '0', '0')
  expect(screen.getAllByText('Not defined (zero total)')).toHaveLength(10)
  expect(screen.queryByText(/= 0.00%/)).not.toBeInTheDocument()
})
it('rejects invalid and increasing counts, then hides old results after an edit', () => {
  render(<GroupCounts storageKey="test" />)
  enter('10', '11', '2', '1')
  expect(screen.getByRole('alert')).toBeVisible()
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  enter('1e2', '1', '2', '1')
  expect(screen.getByRole('alert')).toBeVisible()
  enter('10', '5', '2', '1')
  expect(screen.getByRole('table')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Group 1 before count'), { target: { value: '12' } })
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.getByText(/Counts changed/)).toBeVisible()
})
it('restores only drafts, scopes storage, and handles malformed or unavailable storage', () => {
  const view = render(<GroupCounts storageKey="test" />)
  enter('80', '72', '20', '8')
  view.unmount()
  const restored = render(<GroupCounts storageKey="test" />)
  expect(screen.getByLabelText('Group 1 before count')).toHaveValue('80')
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  restored.rerender(<GroupCounts storageKey="other" />)
  expect(screen.getByLabelText('Group 1 before count')).toHaveValue('')
  restored.unmount()
  localStorage.setItem('broken', '{')
  render(<GroupCounts storageKey="broken" />)
  expect(screen.getByText(/could not be loaded/)).toBeVisible()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  fireEvent.change(screen.getByLabelText('Group 1 before count'), { target: { value: '10' } })
  expect(screen.getByText(/current entries remain/)).toBeVisible()
  expect(screen.getByLabelText('Group 1 before count')).toHaveValue('10')
})
it('bounds groups and rejects duplicate names', () => {
  render(<GroupCounts storageKey="test" />)
  expect(screen.getByRole('button', { name: 'Remove group 1' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('Group name 2'), { target: { value: 'A' } })
  enter('2', '1', '2', '1')
  expect(screen.getByRole('alert')).toBeVisible()
  for (let i = 0; i < 6; i++) fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
  expect(screen.getByRole('button', { name: 'Add group' })).toBeDisabled()
})

it('changing only a group name invalidates the comparison', () => {
  render(<GroupCounts storageKey="names" />)
  enter('10', '5', '2', '1')
  fireEvent.change(screen.getByLabelText('Group name 1'), { target: { value: 'Renamed' } })
  expect(screen.queryByRole('table')).not.toBeInTheDocument()
  expect(screen.getByText(/Counts changed/)).toBeVisible()
})
it('retains editable entries when storage cannot be read', () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
    throw new Error('denied')
  })
  render(<GroupCounts storageKey="denied" />)
  expect(screen.getByText(/could not be loaded/)).toBeVisible()
  expect(screen.getByLabelText('Group 1 before count')).toHaveValue('')
})
