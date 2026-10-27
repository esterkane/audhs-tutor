import { useEffect, useId, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useAreas } from '../features/areas/api'
import { useSkillMap } from '../features/map/api'

/** Whole map first (open learner model): Mermaid picture + an accessible list with the same data. */
export function Map() {
  const [params, setParams] = useSearchParams()
  const areaId = params.get('area') ?? ''
  const areas = useAreas()
  const catalog = areas.data?.areas ?? []
  return (
    <div className="grid gap-4">
      <Card>
        <label htmlFor="map-area" className="block font-medium">
          Map area
        </label>
        <select
          id="map-area"
          className="mt-2 w-full max-w-full min-w-0 rounded border border-line bg-card p-2"
          value={areaId}
          onChange={(event) => {
            const next = new URLSearchParams(params)
            if (event.target.value) next.set('area', event.target.value)
            else next.delete('area')
            setParams(next)
          }}
        >
          <option value="">All areas</option>
          {areaId && !catalog.some((area) => area.id === areaId) && (
            <option value={areaId}>Linked area</option>
          )}
          {catalog.map((area) => (
            <option key={area.id} value={area.id}>
              {area.title}
            </option>
          ))}
        </select>
        <p className="text-sm text-muted mt-2">
          Browsing this map does not change your learning goal or session.
        </p>
        {areas.isError && (
          <p role="alert">
            Area choices could not be refreshed.{' '}
            <Button size="sm" onClick={() => void areas.refetch()} disabled={areas.isFetching}>
              Retry areas
            </Button>
          </p>
        )}
        {areas.isPending && <p role="status">Loading area choices…</p>}
        {areaId && (
          <Link className="underline" to="/map">
            Show all areas
          </Link>
        )}
      </Card>
      <MapContent key={areaId} areaId={areaId} />
    </div>
  )
}

function MapContent({ areaId }: { areaId: string }) {
  const map = useSkillMap(areaId)
  const diagramId = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  const nav = useNavigate()
  const ref = useRef<HTMLDivElement>(null)
  const [svgError, setSvgError] = useState<string | null>(null)
  const [drawing, setDrawing] = useState(true)
  const [retryDiagram, setRetryDiagram] = useState(0)
  const drawSequence = useRef(0)

  useEffect(() => {
    if (!map.data?.nodes.length || !ref.current) return
    let retired = false
    const renderId = `skill-map-${diagramId}-${++drawSequence.current}`
    const timer = setTimeout(() => {
      if (retired) return
      retired = true
      setDrawing(false)
      setSvgError('Drawing timed out. The list below remains available.')
    }, 10000)
    ;(async () => {
      try {
        const mermaid = (await import('mermaid')).default
        if (retired) return
        setDrawing(true)
        setSvgError(null)
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' })
        const { svg } = await mermaid.render(renderId, map.data!.mermaid)
        if (!retired && ref.current) ref.current.innerHTML = svg
      } catch {
        if (!retired) setSvgError('The diagram could not be drawn. The list below remains available.')
      } finally {
        clearTimeout(timer)
        if (!retired) setDrawing(false)
      }
    })()
    return () => {
      retired = true
      clearTimeout(timer)
    }
  }, [map.data, diagramId, retryDiagram])

  const readRecovery = map.isError && (
    <div className="mb-3">
      <p role="alert">
        {map.data
          ? 'Could not refresh the skill map. Showing the last loaded map.'
          : areaId
            ? 'Could not load this area map. The area may be unavailable.'
            : 'Could not load the skill map.'}
      </p>
      <p className="text-sm text-muted">
        {areaId
          ? 'Retry, choose another area, or show all areas.'
          : 'Check that the local app backend is running, then retry.'}
      </p>
      <Button className="mt-2" onClick={() => void map.refetch()} disabled={map.isFetching}>
        Retry loading map
      </Button>
      {map.isFetching && <p role="status">Retrying map…</p>}
      <details className="mt-2">
        <summary>Technical details</summary>
        <p className="text-sm break-words">{map.error.message}</p>
      </details>
    </div>
  )
  if (!map.data)
    return (
      <Card>
        <CardTitle as="h1">Skill map</CardTitle>
        {readRecovery || <p role="status">Loading map…</p>}
        <Link to="/" className="underline">
          Return Home
        </Link>
      </Card>
    )

  function learn(id: string) {
    nav(`/?lesson=${encodeURIComponent(id)}`)
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle as="h1">Skill map</CardTitle>
        {readRecovery}
        <p className="font-medium">{map.data.area_title ?? 'All areas'}</p>
        {areaId && (
          <p className="text-sm text-muted">
            Includes prerequisites from outside this area, labeled in the list below.
          </p>
        )}
        <p className="text-sm text-muted mb-2">
          Mastery is computed from evidence; memory shows items due for review. Locked nodes need their
          prerequisites at 60 %. “Next” uses your current learning settings; this map filter does not change
          it.
        </p>
        {map.data.nodes.length === 0 && (
          <p role="status">
            {areaId
              ? 'No skills are assigned to this area yet. Choose another area or show all areas.'
              : 'No skills are available yet.'}
          </p>
        )}
        {map.data.nodes.length === 0 && (
          <Link className="underline" to="/curriculum">
            Create your first knowledge material
          </Link>
        )}
        <div ref={ref} hidden={map.data.nodes.length === 0} aria-hidden="true" className="overflow-x-auto" />
        {map.data.nodes.length > 0 && drawing && (
          <p role="status" className="text-sm text-muted">
            Drawing the skill map… The list is available below.
          </p>
        )}
        {svgError && (
          <div className="text-sm text-muted">
            <p role="status">{svgError}</p>
            <Button
              disabled={drawing}
              onClick={() => {
                setDrawing(true)
                setRetryDiagram((value) => value + 1)
              }}
            >
              Retry diagram
            </Button>
          </div>
        )}
      </Card>
      <Card>
        <CardTitle>Nodes</CardTitle>
        <ol className="grid gap-2">
          {map.data.nodes.map((n) => (
            <li key={n.id as string} className="flex flex-wrap items-center gap-2 border-b border-line pb-2">
              <span className="font-medium">{n.title as string}</span>
              {Boolean(n.outside_area) && (
                <span className="text-sm text-muted">Prerequisite from outside this area</span>
              )}
              <span className="text-sm text-muted">
                mastery {Math.round((n.mastery as number) * 100)}% · {n.unlocked ? 'unlocked' : 'locked'}
                {n.is_next ? ' · next' : ''} · {(n.memory as { items: number; due: number }).items} items,{' '}
                {(n.memory as { due: number }).due} due
              </span>
              {map.data.edges.some((edge) => edge.kind === 'prerequisite' && edge.to === n.id) && (
                <span className="w-full text-sm text-muted">
                  Prerequisites:{' '}
                  {map.data.edges
                    .filter((edge) => edge.kind === 'prerequisite' && edge.to === n.id)
                    .map((edge) =>
                      String(map.data.nodes.find((parent) => parent.id === edge.from)?.title ?? edge.from),
                    )
                    .join(', ')}
                </span>
              )}
              <Button size="sm" disabled={!n.unlocked} onClick={() => learn(n.id as string)}>
                {n.unlocked ? 'Learn this' : 'Locked'}
              </Button>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  )
}
