import { useMemo, useState } from 'react'
import {
  ReactFlow,
  Controls,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type Connection,
  applyNodeChanges,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { connectPreset } from './connections'
import type { Preset } from './engine'

export default function BlockCanvas({
  preset,
  onChange,
  onInspect,
}: {
  preset: Preset
  onChange: (preset: Preset) => void
  onInspect: (id: string) => void
}) {
  const [layout, setLayout] = useState<Record<string, Partial<Node>>>(() => Object.create(null))
  const [message, setMessage] = useState('')
  const nodes: Node[] = useMemo(
    () => [
      ...preset.nodes.map((n, i) => ({
        id: n.id,
        type: 'input' in n ? 'default' : 'input',
        position: layout[n.id]?.position ?? { x: (i % 3) * 240, y: Math.floor(i / 3) * 120 },
        data: { label: `${n.id} · ${n.type}${'feature' in n ? ` (${n.feature})` : ''}` },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: {
          background: 'var(--color-card)',
          color: 'var(--color-fg)',
          border: '2px solid #777',
          width: 190,
        },
        domAttributes: {
          onKeyDown: (e: React.KeyboardEvent) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              onInspect(n.id)
            }
          },
        },
        measured: layout[n.id]?.measured,
        ariaLabel: `Block ${n.id}, ${n.type}. Select for explanation.`,
      })),
      ...(['scale', 'energy'] as const).map((key, i) => ({
        id: `output:${key}`,
        type: 'output',
        measured: layout[`output:${key}`]?.measured,
        position: layout[`output:${key}`]?.position ?? {
          x: i * 260,
          y: Math.ceil(preset.nodes.length / 3) * 120 + 40,
        },
        data: {
          label:
            key === 'scale'
              ? 'Visual size (0.1–2)'
              : preset.visual.kind === 'rings'
                ? 'Energy (unused by rings)'
                : 'Visual energy (0–1)',
        },
        targetPosition: Position.Left,
        style: { width: 210 },
      })),
    ],
    [preset, layout, onInspect],
  )
  const edges: Edge[] = [
    ...preset.nodes.flatMap((n) =>
      'input' in n ? [{ id: `in:${n.id}`, source: n.input, target: n.id }] : [],
    ),
    ...(['scale', 'energy'] as const).map((key) => ({
      id: `out:${key}`,
      source: preset.visual[key],
      target: `output:${key}`,
      style: key === 'energy' && preset.visual.kind === 'rings' ? { strokeDasharray: '5 5' } : undefined,
    })),
  ].map((e) => ({ ...e, markerEnd: { type: MarkerType.ArrowClosed }, animated: false }))
  function connect(c: Connection) {
    try {
      onChange(connectPreset(preset, c.source, c.target))
      setMessage('Connection updated in the draft. Apply preset to use it.')
    } catch (e) {
      setMessage(`Connection rejected; previous draft kept. ${e instanceof Error ? e.message : ''}`)
    }
  }
  return (
    <div className="grid gap-2">
      <p className="text-sm">
        Drag blocks to arrange them. Drag from a right connector to a left connector to replace its input.
        Layout is temporary. Apply changes the preview; Save applied preset keeps your connections in this
        browser. Keyboard connection controls are below.
      </p>
      <div
        style={{ height: 360 }}
        className="border border-line rounded"
        aria-label="Interactive block canvas"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onConnect={connect}
          onNodesChange={(changes) => {
            const changed = applyNodeChanges(changes, nodes)
            setLayout(
              Object.fromEntries(changed.map((n) => [n.id, { position: n.position, measured: n.measured }])),
            )
          }}
          onNodeClick={(_, n) => {
            if (!n.id.startsWith('output:')) onInspect(n.id)
          }}
          deleteKeyCode={null}
          edgesReconnectable={false}
          nodesDraggable
          fitView
          minZoom={0.2}
          maxZoom={2}
          zoomOnScroll={false}
          preventScrolling={false}
        >
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      {message && (
        <p role="status" className="text-sm">
          {message}
        </p>
      )}
    </div>
  )
}
