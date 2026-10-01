import { useEffect, useRef } from 'react'
import { experimentSnapshot, type ExperimentId } from './experiments'
import { draw } from './render'
export function ComparisonPicture({ id, changed }: { id: ExperimentId; changed: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null)
  const snapshot = experimentSnapshot(id, changed)
  useEffect(() => {
    const s = experimentSnapshot(id, changed)
    if (ref.current) draw(ref.current, s.preset, s.scale, s.energy)
  }, [id, changed])
  return (
    <figure>
      <figcaption>
        {changed ? 'After' : 'Before'} · size {snapshot.scale.toFixed(3)}
      </figcaption>
      <canvas
        width={480}
        height={260}
        ref={ref}
        className="w-full rounded"
        aria-label={`${changed ? 'After' : 'Before'} comparison: ring size ${snapshot.scale.toFixed(3)}`}
      />
    </figure>
  )
}
