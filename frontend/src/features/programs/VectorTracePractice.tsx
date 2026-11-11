import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { useDraftRecovery } from '../curriculum/useDraftRecovery'

const points = [
  { id: 'A', x: 1, y: 3 },
  { id: 'B', x: 3, y: 1 },
  { id: 'C', x: 2, y: 2 },
]
const queries = [
  [2, 1],
  [1, 2],
]
const initial = { prediction: '', step: -1, finished: false }

function Trace({
  projectId,
  variant,
  children,
}: {
  projectId: string
  variant: number
  children?: React.ReactNode
}) {
  const saved = useDraftRecovery(
    'vector-dot-trace-v1:' + projectId + ':' + variant,
    1,
    JSON.stringify(initial),
  )
  let trace: typeof initial
  try {
    trace = JSON.parse(saved.text)
    if (
      !Number.isInteger(trace.step) ||
      trace.step < -1 ||
      trace.step > points.length ||
      !['', ...points.map((p) => p.id)].includes(trace.prediction) ||
      typeof trace.finished !== 'boolean' ||
      (trace.step >= 0 && !trace.prediction)
    )
      throw new Error()
  } catch {
    return (
      <p role="alert">
        The saved trace could not be read.{' '}
        <Button onClick={() => saved.reset(JSON.stringify(initial), 1)}>Restart this trace</Button>
      </p>
    )
  }
  const [qx, qy] = queries[variant]
  const steps = points.map((p) => ({ id: p.id, score: qx * p.x + qy * p.y }))
  function best(count: number) {
    return steps
      .slice(0, count)
      .reduce<(typeof steps)[number] | undefined>(
        (winner, p) => (!winner || p.score > winner.score ? p : winner),
        undefined,
      )
  }
  function move(step: number) {
    saved.edit(JSON.stringify({ ...trace, step, finished: trace.finished || step === points.length }))
  }
  const before = best(trace.step - 1)
  const after = best(trace.step)
  return (
    <section className="grid gap-2" aria-label={variant ? 'Transfer trace' : 'First trace'}>
      <h3>{variant ? 'Transfer: change the query' : 'Trace the running best'}</h3>
      <p>
        Query vector [{qx}, {qy}]. Predict which point will have the highest dot product after the scan.
      </p>
      {trace.step === -1 ? (
        <>
          <label>
            My predicted winner{' '}
            <select
              value={trace.prediction}
              onChange={(e) => saved.edit(JSON.stringify({ ...trace, prediction: e.target.value }))}
            >
              <option value="">Choose a point</option>
              {points.map((p) => (
                <option key={p.id}>{p.id}</option>
              ))}
            </select>
          </label>
          <Button disabled={!trace.prediction} onClick={() => move(0)}>
            Save prediction and start trace
          </Button>
        </>
      ) : (
        <>
          <p>My original prediction: {trace.prediction}</p>
          <div role="status">
            {trace.step === 0 ? (
              'Before the first point: no running best.'
            ) : (
              <>
                Step {trace.step}: point {steps[trace.step - 1].id} scores {qx} × {points[trace.step - 1].x} +{' '}
                {qy} × {points[trace.step - 1].y} = {steps[trace.step - 1].score}. Previous best:{' '}
                {before ? before.id + ' (' + before.score + ')' : 'none'}. Running best: {after!.id} (
                {after!.score}).
                {trace.step === points.length &&
                  ' Your prediction ' +
                    (trace.prediction === after!.id ? 'matches' : 'differs from') +
                    ' the final winner.'}
              </>
            )}
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button disabled={trace.step === 0} variant="secondary" onClick={() => move(trace.step - 1)}>
              Previous point
            </Button>
            <Button disabled={trace.step === points.length} onClick={() => move(trace.step + 1)}>
              Inspect next point
            </Button>
            {trace.finished && (
              <Button variant="secondary" onClick={() => move(0)}>
                Replay from start
              </Button>
            )}
          </div>
        </>
      )}
      {saved.error && <p role="alert">{saved.error}</p>}
      {trace.finished && children}
    </section>
  )
}

export function VectorTracePractice({ projectId }: { projectId: string }) {
  return (
    <Disclosure label="Predict and trace an exact vector search">
      <p>
        Scan these points in order. Multiply corresponding coordinates and add them. Keep the first point on a
        tie. Your predictions and place are saved in this browser tab.
      </p>
      <ul>
        {points.map((p) => (
          <li key={p.id}>
            {p.id}: [{p.x}, {p.y}]
          </li>
        ))}
      </ul>
      <Trace projectId={projectId} variant={0}>
        <Trace projectId={projectId} variant={1} />
      </Trace>
    </Disclosure>
  )
}
