import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { axe } from 'vitest-axe'
import { SampleTrace } from './SampleTrace'
import { initial } from './engine'
it('walks a reproducible sample through feature, smoothing, mapping and output without mutating the preset', async () => {
  const before = JSON.stringify(initial)
  const { container } = render(<SampleTrace preset={initial} />)
  expect(screen.queryByRole('status')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: 'Start sample walkthrough' }))
  expect(screen.getByText('Synthetic bass: 0.571')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Next block' }))
  expect(screen.getByText('Block output: 0.524')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Next block' }))
  expect(screen.getByText('Block output: 0.924')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Next block' }))
  expect(screen.getByText(/Size from size: 0.924/)).toBeVisible()
  expect(screen.getByText(/not used by rings/)).toBeVisible()
  expect(screen.getByRole('button', { name: 'Next block' })).toBeDisabled()
  expect(await axe(container)).toHaveNoViolations()
  fireEvent.click(screen.getByRole('button', { name: 'Restart walkthrough' }))
  expect(screen.getByText('Block output: 0.571')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'End walkthrough' }))
  expect(screen.queryByRole('status')).toBeNull()
  expect(JSON.stringify(initial)).toBe(before)
})
