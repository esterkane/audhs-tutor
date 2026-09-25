import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { experimentSnapshot } from './experiments'
import { GuidedExperiments } from './GuidedExperiments'
it('matches independent arithmetic and repeats from fresh memory', () => {
  expect(experimentSnapshot('feature', false).scale).toBe(0.8)
  expect(experimentSnapshot('feature', true).scale).toBe(0.2)
  expect(experimentSnapshot('smooth', false).scale).toBeCloseTo(0.8 * (1 - Math.exp(-1)))
  expect(experimentSnapshot('smooth', true).scale).toBeCloseTo(0.8 * (1 - Math.exp(-0.2)))
  expect(experimentSnapshot('map', false).rawSize).toBeCloseTo(1.2)
  expect(experimentSnapshot('map', true).rawSize).toBeCloseTo(2.8)
  expect(experimentSnapshot('map', true).scale).toBe(2)
  const first = experimentSnapshot('smooth', true)
  experimentSnapshot('smooth', false)
  expect(experimentSnapshot('smooth', true)).toEqual(first)
})
it('offers context, optional predictions and hints, comparison, restart and exit', async () => {
  const { container } = render(<GuidedExperiments />)
  fireEvent.click(screen.getByRole('button', { name: 'Map a range and see clipping' }))
  expect(screen.getByText(/Mapping changes a number/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Try change and compare' }))
  expect(screen.getByRole('table')).toHaveTextContent('2.800')
  expect(screen.getByRole('table')).toHaveTextContent('2.000')
  expect(await axe(container)).toHaveNoViolations()
  fireEvent.click(screen.getByRole('button', { name: 'Restart experiment' }))
  expect(screen.queryByRole('table')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Stop experiment' }))
  expect(screen.getByRole('button', { name: 'Choose a frequency region' })).toBeVisible()
})
