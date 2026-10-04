import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useAreas } from './api'
import { useBrowseAreas } from './browseState'

/** Visits are navigation history, not evidence of learning or resumable sessions. */
export function RecentAreas({ embedded = false }: { embedded?: boolean }) {
  const Container = embedded ? 'section' : Card
  const { recent, storageError } = useBrowseAreas()
  const areas = useAreas()
  if (!recent.length && !storageError) return null
  const available = recent.flatMap(id => areas.data?.areas.filter(area => area.id === id) ?? []).slice(0, 3)
  const missing = areas.isSuccess && recent.some(id => !areas.data?.areas.some(area => area.id === id))
  return <Container role="region" aria-labelledby="recent-areas-title">
    <CardTitle id="recent-areas-title">Recently browsed areas</CardTitle>
    <p className="text-sm text-muted mb-2">Visits in this tab. Opening an area keeps your saved learning session unchanged.</p>
    {areas.isPending ? <p role="status">Loading recent areas…</p> : areas.isError ? <p role="alert">
      Could not check recent areas. <Button disabled={areas.isFetching} onClick={() => void areas.refetch()}>Retry recent areas</Button>
    </p> : <>
      {!!available.length && <ul className="flex flex-wrap gap-3">{available.map(area => <li key={area.id} className="min-w-0">
        <Link className="underline break-words" to={`/areas?area=${encodeURIComponent(area.id)}`}>{area.title}</Link>
      </li>)}</ul>}
      {missing && <p className="text-sm mt-2">A previously visited area is unavailable. Browse all areas to choose another.</p>}
    </>}
    {storageError && <p role="status" className="text-sm mt-2">Browsing history could not be saved or restored in this tab.</p>}
    <p className="mt-2"><Link className="underline" to="/areas">Browse all areas</Link></p>
  </Container>
}
