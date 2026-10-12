import { ReactFlow, MarkerType, Position } from '@xyflow/react'
import { useId, useState } from 'react'
import '@xyflow/react/dist/style.css'
import './visual-learning.css'

/** Trusted local render input, not an API response or server binding validation. */
export interface RelationshipGraphData {
  title: string
  textEquivalent: string
  directed: boolean
  nodes: ReadonlyArray<{ id: string; label: string; explanation: string }>
  edges: ReadonlyArray<{ id: string; source: string; target: string }>
}
export default function RelationshipGraph({ graph }: { graph: RelationshipGraphData }) {
  const [selected, setSelected] = useState('')
  const helpId = useId()
  const active = graph.nodes.find(node => node.id === selected)
  const nodes = graph.nodes.map((node, i) => ({
    id: node.id, position: { x: i % 2 * 230, y: Math.floor(i / 2) * 130 },
    data: { label: node.label }, sourcePosition: Position.Bottom, targetPosition: Position.Top,
    style: { width: 190, background: 'var(--color-card)', color: 'var(--color-fg)', borderColor: 'var(--color-control)' },
  }))
  return <div className="grid gap-3">
    <div className="learning-flow h-72 border border-line rounded-md" aria-label={graph.title}>
      <ReactFlow nodes={nodes} edges={graph.edges.map(edge => ({ ...edge, type: 'straight', markerEnd: graph.directed ? { type: MarkerType.ArrowClosed } : undefined, animated: false }))} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} nodesFocusable={false} edgesFocusable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} />
    </div>
    <p>{graph.textEquivalent}</p>
    <label htmlFor={helpId}>Explain a part of the diagram</label>
    <select id={helpId} className="block w-full p-3 bg-card border border-control rounded-md" value={active?.id ?? ''} onChange={event => setSelected(event.target.value)}>
      <option value="">Choose a part (optional)</option>
      {graph.nodes.map(node => <option key={node.id} value={node.id}>{node.label}</option>)}
    </select>
    {active && <p role="status">{active.explanation}</p>}
  </div>
}
