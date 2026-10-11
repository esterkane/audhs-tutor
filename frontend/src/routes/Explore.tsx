import { useEffect } from 'react'
import { useBrowseAreas } from '../features/areas/browseState'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useAreas } from '../features/areas/api'
import { boundedRead } from '../lib/boundedRead'
import type { Schemas } from '../lib/api'

export function Explore() {
  const areas = useAreas()
  const [params] = useSearchParams()
  const selected = params.get('area') ?? ''
  const area = areas.data?.areas.find(item => item.id === selected)
  const remember = useBrowseAreas(state => state.remember)
  useEffect(() => { if (area) remember(area.id) }, [area, remember])
  return <div className="grid gap-4">
    <header><h1 className="text-page-title font-semibold">Explore</h1>
      <p className="text-muted mt-2">Choose an area to see what you can learn. Browsing keeps your current session in place.</p></header>
    {areas.isPending && <p role="status">Loading learning areas…</p>}
    {areas.isError && <p role="alert">Could not load learning areas. <Button onClick={() => void areas.refetch()}>Retry areas</Button></p>}
    {!selected && areas.data && <>
      {!areas.data.areas.length && <p>No learning areas yet. Prepare your material to create them.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {areas.data.areas.map(item => <Card key={item.id}>
          <CardTitle><Link className="underline" to={`/explore?area=${encodeURIComponent(item.id)}`}>{item.title}</Link></CardTitle>
          <p className="mt-2">{item.description || 'Open this area to see its available concepts.'}</p>
          <p className="text-sm text-muted mt-2">{item.active_lessons > 0 ? 'Lessons available' : 'Lessons need preparation'}</p>
        </Card>)}
      </div>
    </>}
    {selected && <Link className="underline" to="/explore">All learning areas</Link>}
    {area && <>
      <Card><CardTitle>{area.title}</CardTitle>{area.description && <p className="mt-2">{area.description}</p>}</Card>
      <Concepts key={area.id} areaId={area.id} />
    </>}
    {selected && areas.data && !area && <p role="status">This area is unavailable. Choose another learning area.</p>}
    <Link className="underline" to={area ? `/areas?area=${encodeURIComponent(area.id)}` : '/areas'}>Prepare learning material</Link>
    <Link className="underline" to="/corpus">Open Materials and import diagnostics</Link>
  </div>
}

function Concepts({ areaId }: { areaId: string }) {
  const query = useQuery({
    queryKey: ['area-concepts', areaId],
    queryFn: ({ signal }) => boundedRead<Schemas['AreaConcepts']>(`/api/areas/${encodeURIComponent(areaId)}/concepts`, signal, 'Area concepts'),
    retry: false,
  })
  if (query.isPending) return <p role="status">Loading available concepts…</p>
  if (query.isError) return <p role="alert">Could not load concepts. <Button onClick={() => void query.refetch()}>Retry concepts</Button></p>
  if (!query.data.concepts.length) return <p>No activated lessons in this area yet. Prepare and review its material before choosing a lesson.</p>
  return <section aria-label="Available concepts" className="grid gap-4">
    <h2 className="text-panel-title font-semibold">What you can learn</h2>
    {query.data.concepts.map(concept => <Card key={concept.id}>
      <CardTitle as="h3">{concept.title}</CardTitle>
      {concept.description && <p className="mt-2">{concept.description}</p>}
      {!!concept.success_criteria.length && <ul className="list-disc pl-5 mt-2">{concept.success_criteria.map((criterion, index) => <li key={index}>{criterion}</li>)}</ul>}
      <Button className="mt-3" asChild><Link to={`/?lesson=${encodeURIComponent(concept.id)}`}>Choose this lesson</Link></Button>
    </Card>)}
  </section>
}
