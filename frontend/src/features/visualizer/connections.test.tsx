import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { connectPreset } from './connections'
import { initial } from './engine'
import { ConnectionEditor } from './ConnectionEditor'
it('rewires a single input or binding without mutating the original', () => {
  const p = connectPreset(initial, 'signal', 'size')
  expect(p.nodes.find((n) => n.id === 'size')).toMatchObject({ input: 'signal' })
  expect(initial.nodes.find((n) => n.id === 'size')).toMatchObject({ input: 'soft' })
  expect(connectPreset(initial, 'signal', 'output:scale').visual.scale).toBe('signal')
  expect(connectPreset(initial, 'size', 'output:energy').visual.energy).toBe('size')
})
it('rejects cycles, nonexistent sources and invalid targets without mutation', () => {
  const before = JSON.stringify(initial)
  expect(() => connectPreset(initial, 'size', 'soft')).toThrow()
  expect(() => connectPreset(initial, 'soft', 'soft')).toThrow()
  expect(() => connectPreset(initial, 'absent', 'soft')).toThrow()
  expect(() => connectPreset(initial, 'soft', 'signal')).toThrow()
  expect(() => connectPreset(initial, 'signal', 'output:other')).toThrow()
  expect(JSON.stringify(initial)).toBe(before)
})
it('supports keyboard-native editing without loading the canvas and preserves invalid edits', async () => {
  const change = vi.fn()
  const { container } = render(<ConnectionEditor preset={initial} onChange={change} onInspect={() => {}} />)
  fireEvent.change(screen.getByRole('combobox', { name: 'Input for size' }), { target: { value: 'signal' } })
  expect(change).toHaveBeenCalledTimes(1)
  fireEvent.change(screen.getByRole('combobox', { name: 'Input for soft' }), { target: { value: 'size' } })
  expect(change).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('combobox', { name: 'Input for soft' })).toHaveValue('signal')
  expect(screen.getByRole('status')).toHaveTextContent(/cycl/i)
  expect(screen.queryByLabelText('Interactive block canvas')).toBeNull()
  expect(await axe(container)).toHaveNoViolations()
})
