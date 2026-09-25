import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useSkillMap } from '../features/map/api'

/** Whole map first (open learner model): Mermaid picture + an accessible list with the same data. */
export function Map() {
  const map = useSkillMap()
  const nav = useNavigate()
  const ref = useRef<HTMLDivElement>(null)
  const [svgError, setSvgError] = useState<string | null>(null)

  useEffect(() => {
    if (!map.data || !ref.current) return
    let cancelled = false
    ;(async () => {
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' })
        const { svg } = await mermaid.render('skill-map-svg', map.data!.mermaid)
        if (!cancelled && ref.current) ref.current.innerHTML = svg
      } catch (e) {
        if (!cancelled) setSvgError((e as Error).message)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [map.data])

  if (map.isLoading || !map.data) return <Card>Loading map…</Card>

  function learn(id: string) {
    nav(`/?lesson=${encodeURIComponent(id)}`)
  }

  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Skill map</CardTitle>
        <p className="text-sm text-muted mb-2">
          Mastery is computed from evidence; memory shows items due for review. Locked nodes need their
          prerequisites at 60 %.
        </p>
        <div ref={ref} aria-hidden="true" className="overflow-x-auto" />
        {svgError && (
          <p className="text-sm text-muted">
            Diagram unavailable ({svgError}); the list below has the same information.
          </p>
        )}
      </Card>
      <Card>
        <CardTitle>Nodes</CardTitle>
        <ol className="grid gap-2">
          {map.data.nodes.map((n) => (
            <li key={n.id as string} className="flex flex-wrap items-center gap-2 border-b border-line pb-2">
              <span className="font-medium">{n.title as string}</span>
              <span className="text-sm text-muted">
                mastery {Math.round((n.mastery as number) * 100)}% · {n.unlocked ? 'unlocked' : 'locked'}
                {n.is_next ? ' · next' : ''} · {(n.memory as { items: number; due: number }).items} items,{' '}
                {(n.memory as { due: number }).due} due
              </span>
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
