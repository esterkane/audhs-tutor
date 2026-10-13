import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RelationshipGraph, { type RelationshipGraphData } from './RelationshipGraph'
vi.mock('@xyflow/react', () => ({ ReactFlow: () => <div>Diagram</div>, MarkerType: { ArrowClosed: 'arrow' }, Position: { Bottom: 'bottom', Top: 'top' } }))
const graph: RelationshipGraphData = {
  title: 'Example', textEquivalent: 'A single concept.', directed: true,
  nodes: [{ id: 'a', label: 'Concept', explanation: '<img src="https://example.com/x" onerror="alert(1)">' }], edges: [],
}
describe('relationship help', () => {
  it('renders explanations literally and follows updated content without losing selection', () => {
    const { container, rerender } = render(<RelationshipGraph graph={graph} />)
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'a' } })
    expect(screen.getByRole('status').textContent).toBe(graph.nodes[0].explanation)
    expect(container.querySelector('img')).toBeNull()
    rerender(<RelationshipGraph graph={{ ...graph, nodes: [{ ...graph.nodes[0], explanation: 'Updated explanation' }] }} />)
    expect(screen.getByRole('status').textContent).toBe('Updated explanation')
    expect(screen.getByRole('combobox')).toHaveValue('a')
    rerender(<RelationshipGraph graph={{ ...graph, nodes: [] }} />)
    expect(screen.queryByRole('status')).toBeNull()
    expect(screen.getByRole('combobox')).toHaveValue('')
  })
})

it('preserves named directed connections as readable literal text', () => {
  render(<RelationshipGraph graph={{ ...graph, nodes: [
    { id: 'a', label: 'Training data', explanation: 'Input' },
    { id: 'b', label: 'Mean', explanation: 'Parameter' },
  ], edges: [{ id: 'ab', source: 'a', target: 'b', label: 'fits <script>not code</script>' }] }} />)
  expect(screen.getByText('Read connections as text')).toBeInTheDocument()
  expect(screen.getByText('Training data → Mean: fits <script>not code</script>')).toBeInTheDocument()
})
