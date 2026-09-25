import { fireEvent, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { Visualizer } from '../../routes/Visualizer'
import { initial } from './engine'
import { describeBlock } from './explanations'
import { examples } from './examples'
import { jsonResponse, renderApp } from '../../test/utils'
beforeEach(() => {
  localStorage.clear()
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse({ values: { 'ui.reduced_motion': true } })),
  )
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})
it('edits one shared draft and labels unapplied explanations without changing the working preset', async () => {
  const { container } = renderApp(<Visualizer />)
  fireEvent.change(screen.getByLabelText('Visual style'), { target: { value: 'orbit' } })
  expect(JSON.parse((screen.getByLabelText('Preset JSON') as HTMLTextAreaElement).value).visual.kind).toBe(
    'orbit',
  )
  fireEvent.click(screen.getByText('Block controls (3)'))
  fireEvent.change(screen.getByLabelText('Feature for signal'), { target: { value: 'treble' } })
  fireEvent.click(screen.getByRole('button', { name: 'Explain signal' }))
  expect(screen.getByText(/signal reads treble/)).toBeVisible()
  expect(screen.getByText(/current visual values belong to the previous preset/)).toBeVisible()
  expect(localStorage.getItem('audhs:visualizer:preset:v1')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Apply preset' }))
  expect(screen.getByText(/Last displayed block value/)).toBeVisible()
  expect(await axe(container)).toHaveNoViolations()
})
it('retains custom saved work when loading an example and recovers from invalid JSON', () => {
  renderApp(<Visualizer />)
  fireEvent.click(screen.getByRole('button', { name: 'Save applied preset' }))
  const saved = localStorage.getItem('audhs:visualizer:preset:v1')
  fireEvent.click(screen.getByText('Choose an example'))
  fireEvent.click(screen.getByRole('button', { name: 'Load Slow oscillator' }))
  expect(screen.getByText(/Active preset: Bass rings/)).toBeVisible()
  expect(localStorage.getItem('audhs:visualizer:preset:v1')).toBe(saved)
  fireEvent.change(screen.getByLabelText('Preset JSON'), { target: { value: '{' } })
  expect(screen.getByText(/Controls need a valid preset/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Load Bass rings' }))
  expect(screen.getByLabelText('Visual style')).toHaveValue('rings')
})
it('explains smoothing time constants and a zero-frequency oscillator accurately', () => {
  expect(describeBlock(initial, 'soft')?.mechanism).toContain('not fixed completion deadlines')
  const p = structuredClone(examples[2].preset)
  const n = p.nodes[0]
  if (n.type === 'lfo') n.frequencyHz = 0
  expect(describeBlock(p, 'wave')?.mechanism).toContain('half the amplitude')
  expect(describeBlock(p, 'absent')).toBeNull()
})

it('allows negative numeric edits and reports invalid values without changing the draft', () => {
  renderApp(<Visualizer />)
  fireEvent.click(screen.getByText('Block controls (3)'))
  const field = screen.getByLabelText('Output start for size')
  fireEvent.change(field, { target: { value: '-0.5' } })
  fireEvent.blur(field)
  expect(
    JSON.parse((screen.getByLabelText('Preset JSON') as HTMLTextAreaElement).value).nodes[2].outputRange[0],
  ).toBe(-0.5)
  const updated = screen.getByLabelText('Output start for size')
  fireEvent.change(updated, { target: { value: '1000' } })
  fireEvent.blur(updated)
  expect(screen.getByText(/previous value was kept/)).toBeVisible()
  expect(updated).toHaveValue(-0.5)
})
