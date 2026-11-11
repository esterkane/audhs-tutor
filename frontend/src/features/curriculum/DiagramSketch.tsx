import { useId, useMemo, useRef, useState, type PointerEvent } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { useDraftRecovery } from './useDraftRecovery'

type Drawing = { lines: string[]; description: string; reflection: string; compare: boolean }
const empty = JSON.stringify({ lines: [], description: '', reflection: '', compare: false })
const maxLines = 80
function restore(raw: string): Drawing | null {
  try {
    const s = JSON.parse(raw)
    if (
      !Array.isArray(s.lines) ||
      s.lines.length > maxLines ||
      !s.lines.every(
        (line: unknown) =>
          typeof line === 'string' &&
          line.length <= 2000 &&
          /^\d{1,3},\d{1,3}( \d{1,3},\d{1,3})*$/.test(line),
      ) ||
      typeof s.description !== 'string' ||
      typeof s.reflection !== 'string' ||
      typeof s.compare !== 'boolean'
    )
      return null
    return s
  } catch {
    return null
  }
}
export function DiagramSketch({
  identity,
  source,
  label,
}: {
  identity: string
  source: Schemas['AcceptedPdfSource']
  label: Schemas['DiagramLabel']
}) {
  const saved = useDraftRecovery(
    'diagram-sketch:' + identity + ':' + source.version_id + ':' + label.page,
    1,
    empty,
  )
  const state = useMemo(() => restore(saved.text), [saved.text])
  const pending = useRef<{ id: number; points: string[] } | null>(null)
  const [line, setLine] = useState('')
  const [image, setImage] = useState(false)
  const [failed, setFailed] = useState(false)
  const caption = useId()
  const src =
    '/api/knowledge-material/uploads/' +
    encodeURIComponent(source.upload_id) +
    '/versions/' +
    encodeURIComponent(source.version_id) +
    '/pages/' +
    label.page +
    '/preview'
  function change(fields: Partial<Drawing>) {
    if (state) saved.edit(JSON.stringify({ ...state, ...fields }))
  }
  function point(e: PointerEvent<SVGSVGElement>) {
    const stroke = pending.current
    if (!stroke || stroke.id !== e.pointerId) return
    const b = e.currentTarget.getBoundingClientRect()
    const coordinate = (v: number, n: number) => Math.round(Math.max(0, Math.min(v, n)))
    const p =
      coordinate(((e.clientX - b.left) * 400) / b.width, 400) +
      ',' +
      coordinate(((e.clientY - b.top) * 240) / b.height, 240)
    if (p !== stroke.points.at(-1)) {
      if (stroke.points.length >= 240) stroke.points = stroke.points.filter((_, i) => i % 2 === 0)
      stroke.points.push(p)
    }
    setLine(stroke.points.join(' '))
  }
  function finish(e: PointerEvent<SVGSVGElement>, keep: boolean) {
    const stroke = pending.current
    if (!stroke || stroke.id !== e.pointerId || !state) return
    if (keep) {
      point(e)
      if (stroke.points.length === 1) stroke.points.push(stroke.points[0])
      change({ lines: [...state.lines, stroke.points.join(' ')] })
    }
    pending.current = null
    setLine('')
  }
  return (
    <Disclosure label="Sketch or describe the diagram">
      <p>
        Reconstruct page {label.page} from memory. Draw, describe it in words, or use both. Your practice
        stays in this tab.
      </p>
      {!state ? (
        <p role="alert">
          This practice could not be restored.{' '}
          <Button onClick={() => saved.reset(empty, 1)}>Start a new sketch</Button>
        </p>
      ) : (
        <>
          <label className="block">
            My description of the diagram
            <textarea
              className="block w-full rounded border p-2"
              maxLength={4000}
              value={state.description}
              onChange={(e) => change({ description: e.target.value })}
            />
          </label>
          <Disclosure label="Draw with a pointer">
            <svg
              role="img"
              aria-label="Sketch pad"
              viewBox="0 0 400 240"
              preserveAspectRatio="none"
              className="w-full max-w-lg aspect-[5/3] touch-none rounded border bg-card"
              onPointerDown={(e) => {
                if (!e.isPrimary || e.button !== 0 || pending.current || state.lines.length >= maxLines)
                  return
                e.currentTarget.setPointerCapture(e.pointerId)
                pending.current = { id: e.pointerId, points: [] }
                point(e)
              }}
              onPointerMove={point}
              onPointerUp={(e) => finish(e, true)}
              onPointerCancel={(e) => finish(e, false)}
              onLostPointerCapture={(e) => finish(e, false)}
            >
              {[...state.lines, ...(line ? [line] : [])].map((p, i) => (
                <polyline
                  key={i}
                  points={p}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={3}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
              ))}
            </svg>
            <Button
              disabled={!state.lines.length}
              onClick={() => change({ lines: state.lines.slice(0, -1) })}
            >
              Undo last stroke
            </Button>
            {state.lines.length >= maxLines && (
              <p role="status">
                The sketch has reached its stroke limit. Undo a stroke or continue in words.
              </p>
            )}
          </Disclosure>
          <Button
            aria-expanded={state.compare}
            onClick={() => {
              change({ compare: !state.compare })
              setImage(false)
              setFailed(false)
            }}
          >
            {state.compare ? 'Hide diagram comparison' : 'Compare with the authored diagram'}
          </Button>
          {state.compare && (
            <section aria-label="Diagram comparison">
              <p id={caption}>
                <strong>
                  Author’s description, page {label.page}
                  {label.position ? ', ' + label.position : ''}:{' '}
                </strong>
                {label.text}
              </p>
              <Button
                aria-expanded={image}
                onClick={() => {
                  setImage(!image)
                  setFailed(false)
                }}
              >
                {image ? 'Hide source image' : 'Inspect source image'}
              </Button>
              {image &&
                (failed ? (
                  <p role="status">The image is unavailable. The author’s description is shown above.</p>
                ) : (
                  <img
                    src={src}
                    className="max-w-full h-auto"
                    alt={'Original diagram on page ' + label.page}
                    aria-describedby={caption}
                    onError={() => setFailed(true)}
                  />
                ))}
              <label className="block">
                What matched or changed? (optional)
                <textarea
                  className="block w-full rounded border p-2"
                  maxLength={4000}
                  value={state.reflection}
                  onChange={(e) => change({ reflection: e.target.value })}
                />
              </label>
            </section>
          )}
        </>
      )}
      {saved.error && <p role="alert">{saved.error}</p>}
    </Disclosure>
  )
}
