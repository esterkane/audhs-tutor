import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { useAreas } from './api'
import { useBrowseAreas } from './browseState'

export function BrowseArea() {
  const areas = useAreas()
  const { current, recent, storageError } = useBrowseAreas()
  const navigate = useNavigate()
  const catalog = areas.data?.areas ?? []
  const selected = catalog.find(area => area.id === current)
  const recentAreas = recent.flatMap(id => catalog.filter(area => area.id === id))
  return <details className="min-w-0">
    <summary className="cursor-pointer text-sm">Browse area{selected ? ` · ${selected.title}` : ''}</summary>
    <div className="grid gap-2 mt-2 max-w-md">
      <p className="text-sm text-muted">Browse material without changing your learning session.</p>
      {areas.isPending && <p role="status">Loading areas…</p>}
      {areas.isError && <div role="alert">
        Could not refresh areas. {areas.data ? 'Showing the last loaded list.' : ''}
        <Button onClick={() => void areas.refetch()} disabled={areas.isFetching}>Retry areas</Button>
      </div>}
      {areas.data && <label className="text-sm">
        Area to browse
        <select className="block w-full min-w-0 max-w-full border border-line bg-card rounded p-2" value={selected?.id ?? ''}
          onChange={event => navigate(event.target.value ? `/areas?area=${encodeURIComponent(event.target.value)}` : '/areas')}>
          <option value="">All learning areas</option>
          {!!recentAreas.length && <optgroup label="Recent in this tab">{recentAreas.map(area => <option key={area.id} value={area.id}>{area.title}</option>)}</optgroup>}
          <optgroup label="All areas">{catalog.filter(area => !recent.includes(area.id)).map(area => <option key={area.id} value={area.id}>{area.title}</option>)}</optgroup>
        </select>
      </label>}
      <Link className="underline text-sm" to={selected ? `/areas?area=${encodeURIComponent(selected.id)}` : '/areas'}>{selected ? 'Open this area' : 'Open all learning areas'}</Link>
      {areas.isSuccess && !catalog.length && <p className="text-sm">No areas yet. Open Learning areas to prepare them.</p>}
      {areas.isSuccess && current && !selected && <p className="text-sm">The previously browsed area is unavailable. Choose another area.</p>}
      {storageError && <p role="status" className="text-sm">Browsing history could not be saved in this tab.</p>}
    </div>
  </details>
}
