import { ReactFlow, MarkerType, Position } from '@xyflow/react'
import { useEffect, useId, useRef, useState } from 'react'
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
export default function RelationshipGraph({ graph, showTextEquivalent = true }: { graph: RelationshipGraphData; showTextEquivalent?: boolean }) {
  const [selected, setSelected] = useState('')
  const frame = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const observer = new ResizeObserver(entries => {
      const width = entries[0]?.contentRect.width ?? 0
      if (width > 0) setWidth(Math.round(width))
    })
    if (frame.current) observer.observe(frame.current)
    return () => observer.disconnect()
  }, [])
  const columns = width < 480 ? 1 : 2
  const helpId = useId()
  const active = graph.nodes.find(node => node.id === selected)
  const nodes = graph.nodes.map((node, i) => ({
    id: node.id, position: { x: i % columns * 230, y: Math.floor(i / columns) * 130 },
    data: { label: node.label }, sourcePosition: Position.Bottom, targetPosition: Position.Top,
    style: { width: 190, background: 'var(--color-card)', color: 'var(--color-fg)', borderColor: 'var(--color-control)' },
  }))
  return <div className="grid gap-3">
    <div ref={frame} className="learning-flow max-h-96 overflow-auto border border-line rounded-md" role="region" tabIndex={0} aria-label={`${graph.title}: scrollable diagram`}>
      <div style={{ height: Math.max(288, Math.ceil(graph.nodes.length / columns) * 130 + 80) }}>
      <ReactFlow key={`${columns}:${width}`} fitViewOptions={{ maxZoom: 1.2 }} nodes={nodes} edges={graph.edges.map((edge, index) => ({ ...edge, label: String(index + 1), type: 'straight', labelStyle: { fill: 'var(--color-fg)' }, labelBgStyle: { fill: 'var(--color-card)' }, markerEnd: graph.directed ? { type: MarkerType.ArrowClosed } : undefined, animated: false }))} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} nodesFocusable={false} edgesFocusable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} />
      </div>
    </div>
    {showTextEquivalent && <p>{graph.textEquivalent}</p>}
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
