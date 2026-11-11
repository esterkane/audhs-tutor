import { render, screen, within } from '@testing-library/react'
import { expect, it } from 'vitest'
import { VisualDescription } from './VisualDescription'

it('reads an undirected connection symmetrically with authored labels and no graph renderer', async () => {
  render(
    <VisualDescription
      value={{
        directed: false,
        text_equivalent: 'The topics share a dataset.',
        nodes: [
          { id: 'alpha', label: 'Training', explanation: 'Fit parameters.' },
          { id: 'beta', label: 'Evaluation', explanation: 'Measure results.' },
        ],
        edges: [{ id: 'edge1', source: 'beta', target: 'alpha', label: 'Use separate partitions' }],
      }}
    />,
  )
  const summary = screen.getByText('Read all concepts and relationships').closest('summary')!
  summary.focus()
  expect(summary).toHaveFocus()
  summary.click()
  const list = screen.getByRole('list', { name: 'Numbered diagram connections' })
  expect(within(list).getByRole('listitem')).toHaveTextContent(
    'Between Evaluation and Training: Use separate partitions',
  )
})
