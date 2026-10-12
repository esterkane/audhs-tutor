import { ReactFlow, MarkerType, Position } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './visual-learning.css'
import type { FitScope } from './leakage'
export default function LeakageGraph({ scope, mean }: { scope: FitScope; mean: number }) {
  const labels = ['Training values', 'Held-out values', `Fit mean = ${mean}`, 'Apply the same mean']
  const nodes = labels.map((label, i) => ({ id: String(i), position: { x: i % 2 * 230, y: Math.floor(i / 2) * 130 }, data: { label }, sourcePosition: Position.Bottom, targetPosition: Position.Top, style: { width: 190, background: 'var(--color-card)', color: 'var(--color-fg)', borderColor: 'var(--color-control)' } }))
  const pairs = scope === 'train' ? [[0, 2], [0, 3], [2, 3], [1, 3]] : [[0, 2], [0, 3], [1, 2], [2, 3], [1, 3]]
  return <div className="learning-flow h-72 border border-line rounded-md" aria-label="Preprocessing information flow">
    <ReactFlow nodes={nodes} edges={pairs.map(([a,b]) => ({ id: `${a}-${b}`, type: 'straight', source: String(a), target: String(b), markerEnd: { type: MarkerType.ArrowClosed }, animated: false }))} fitView nodesDraggable={false} nodesConnectable={false} elementsSelectable={false} nodesFocusable={false} edgesFocusable={false} panOnDrag={false} zoomOnScroll={false} zoomOnPinch={false} zoomOnDoubleClick={false} preventScrolling={false} />
  </div>
}
