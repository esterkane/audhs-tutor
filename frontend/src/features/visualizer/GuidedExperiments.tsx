import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { experiments, experimentSnapshot, type ExperimentId } from './experiments'

export function GuidedExperiments() {
  const [active, setActive] = useState<ExperimentId | null>(null)
  const [compared, setCompared] = useState(false)
  const [hint, setHint] = useState(false)
  const [prediction, setPrediction] = useState('')
  const lesson = experiments.find((e) => e.id === active)
  function reset() {
    setCompared(false)
    setHint(false)
    setPrediction('')
  }
  if (!lesson)
    return (
      <div className="grid gap-2">
        <p className="text-sm">
          Choose a short experiment. Each uses fixed made-up values and leaves your picture, draft and audio
          playback unchanged.
        </p>
        {experiments.map((e) => (
          <Button
            key={e.id}
            variant="outline"
            onClick={() => {
              reset()
              setActive(e.id)
            }}
          >
            {e.title}
          </Button>
        ))}
      </div>
    )
  const before = experimentSnapshot(lesson.id, false)
  const after = compared ? experimentSnapshot(lesson.id, true) : null
  return (
    <section aria-label="Guided comparison" className="grid gap-3">
      <h3 className="font-medium">{lesson.title}</h3>
      <p>{lesson.context}</p>
      <p>{lesson.change}</p>
      <label className="grid gap-1 text-sm">
        Optional prediction: what will happen to size?
        <select
          className="bg-card border border-line rounded p-2"
          value={prediction}
          onChange={(e) => setPrediction(e.target.value)}
        >
          <option value="">Skip prediction</option>
          <option>Smaller</option>
          <option>Larger</option>
          <option>Unchanged</option>
        </select>
      </label>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => setHint(!hint)}>
          {hint ? 'Hide experiment hint' : 'Show experiment hint'}
        </Button>
        <Button variant="primary" onClick={() => setCompared(true)}>
          Try change and compare
        </Button>
      </div>
      {hint && <p>{lesson.hint}</p>}
      {after && (
        <div className="grid gap-2">
          <p role="status">Comparison ready. Your main picture and audio are unchanged.</p>
          <div className="overflow-x-auto">
            <table className="text-sm w-full text-left">
              <caption className="text-left">
                Fixed synthetic sample · time 0.1 s · step 0.1 s · fresh memory for each version
              </caption>
              <thead>
                <tr>
                  <th scope="col">Value</th>
                  <th scope="col">Before</th>
                  <th scope="col">After</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Block output before visual clipping</th>
                  <td>{before.rawSize.toFixed(3)}</td>
                  <td>{after.rawSize.toFixed(3)}</td>
                </tr>
                <tr>
                  <th scope="row">Rendered size (0.1–2)</th>
                  <td>{before.scale.toFixed(3)}</td>
                  <td>{after.scale.toFixed(3)}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>{lesson.explanation}</p>
          <p className="text-sm text-muted">
            Rings uses size only. Its energy binding does not change the image. This sample time is
            independent of file playback; replaying a real file section is approximate, not an identical
            numerical comparison.
          </p>
          <details>
            <summary className="cursor-pointer">Comparison settings and raw input</summary>
            <pre className="whitespace-pre-wrap break-all text-xs">
              {JSON.stringify({ before, after }, null, 2)}
            </pre>
          </details>
          <p className="text-sm">
            Optional reflection: explain what changed using the input, transformation and output. This
            practice is not graded or recorded as mastery.
          </p>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={reset}>
          Restart experiment
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            reset()
            setActive(null)
          }}
        >
          Stop experiment
        </Button>
      </div>
    </section>
  )
}
