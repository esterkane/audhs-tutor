import { fireEvent, render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { SignalFlow } from './SignalFlow'
import { initial } from './engine'
it('shows actual dependency edges and separate visual bindings with accessible inspection', async () => {
  const inspect = vi.fn()
  const { container } = render(<SignalFlow preset={initial} draft selected="soft" onInspect={inspect} />)
  expect(screen.getByText(/Draft connections/)).toBeVisible()
  const rows = within(screen.getByRole('list', { name: 'Block connections' })).getAllByRole('listitem')
  expect(within(rows[0]).getByText('Audio or demo: bass')).toBeVisible()
  expect(within(rows[1]).getByRole('button', { name: 'Inspect signal' })).toBeVisible()
  expect(within(rows[1]).getByRole('button', { name: 'Inspect soft', pressed: true })).toBeVisible()
  fireEvent.click(within(rows[2]).getByRole('button', { name: 'Inspect size' }))
  expect(inspect).toHaveBeenCalledWith('size')
  const visual = screen.getByLabelText('Visual connections')
  expect(within(visual).getByRole('button', { name: 'Inspect size' })).toBeVisible()
  expect(within(visual).getByRole('button', { name: 'Inspect soft' })).toBeVisible()
  expect(within(visual).getByText(/energy \(not used by rings\)/)).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
})
it('does not invent audio or sequential dependencies for independent nodes', () => {
  render(
    <SignalFlow
      preset={{
        ...initial,
        nodes: [
          { id: 'fixed', type: 'constant', value: 1 },
          { id: 'clock', type: 'lfo', frequencyHz: 1, amplitude: 1 },
        ],
        visual: { ...initial.visual, scale: 'fixed', energy: 'clock' },
      }}
      draft={false}
      selected=""
      onInspect={() => {}}
    />,
  )
  expect(screen.getByText('Applied connections.', { exact: false })).toBeVisible()
  const rows = within(screen.getByRole('list')).getAllByRole('listitem')
  expect(within(rows[1]).queryByRole('button', { name: 'Inspect fixed' })).toBeNull()
  expect(within(rows[1]).getByText('Elapsed time (independent of audio)')).toBeVisible()
})
