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
  edges: ReadonlyArray<{ id: string; source: string; target: string; label: string }>
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
      <ReactFlow nodes={nodes} edges={graph.edges.map((edge, index) => ({ ...edge, label: String(index + 1), type: 'straight', labelStyle: { fill: 'var(--color-fg)' }, labelBgStyle: { fill: 'var(--color-card)' }, markerEnd: graph.directed ? { type: MarkerType.ArrowClosed } : undefined, animated: false }))} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} nodesFocusable={false} edgesFocusable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} />
    </div>
    <p>{graph.textEquivalent}</p>
    {graph.edges.length > 0 && <details className="border border-line rounded-md p-3">
      <summary className="cursor-pointer">Read connections as text</summary>
      <p className="text-sm text-muted mt-2">Numbers in the diagram match this list.</p>
      <ol className="list-decimal pl-5 mt-2 space-y-2 break-words">
        {graph.edges.map(edge => <li key={edge.id}>{`${graph.nodes.find(node => node.id === edge.source)?.label ?? edge.source} ${graph.directed ? '→' : '—'} ${graph.nodes.find(node => node.id === edge.target)?.label ?? edge.target}: ${edge.label}`}</li>)}
      </ol>
    </details>}
    <label htmlFor={helpId}>Explain a part of the diagram</label>
    <select id={helpId} className="block w-full p-3 bg-card border border-control rounded-md" value={active?.id ?? ''} onChange={event => setSelected(event.target.value)}>
      <option value="">Choose a part (optional)</option>
      {graph.nodes.map(node => <option key={node.id} value={node.id}>{node.label}</option>)}
    </select>
    {active && <p role="status">{active.explanation}</p>}
  </div>
}
