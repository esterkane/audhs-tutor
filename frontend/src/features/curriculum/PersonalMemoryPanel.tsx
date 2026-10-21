import { useState } from 'react'
import type { Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

export function PersonalMemoryPanel({ ids, disabled, onChange, onSearch }: {
  ids: string[]; disabled: boolean; onChange: (ids: string[]) => void
  onSearch: (query: string) => Promise<Schemas['PersonalMemory'][]>
}) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<Schemas['PersonalMemory'][]>([])
  const [error, setError] = useState('')
  return <section aria-label="Earlier personal notes" className="space-y-3">
    <p>Find earlier writing in your knowledge library. Choose up to three excerpts for the tutor; these are personal notes, not verified sources.</p>
    <label className="block">Search earlier notes<input className="block w-full rounded border border-line bg-card p-2" maxLength={2000} value={query} disabled={disabled} onChange={e => setQuery(e.target.value)} /></label>
    <Button variant="secondary" disabled={disabled || !query.trim()} onClick={() => {
      setError(''); void onSearch(query).then(result => { setHits(result); if (!result.length) setError('No earlier personal notes found. Try another term or continue with this source.') }).catch(e => setError(e instanceof Error ? e.message : 'Search unavailable. Your writing is kept.'))
    }}>Find earlier notes</Button>
    {!!ids.length && <div><p>{ids.length} earlier note excerpts selected for tutor context.</p><Button variant="secondary" disabled={disabled} onClick={() => onChange([])}>Remove selected earlier notes</Button></div>}
    {hits.map(m => <article key={m.id} className="rounded border border-line p-3 space-y-2">
      <p className="font-semibold">{m.title} · saved version {m.version}</p>
      <p className="text-sm text-muted">{m.kind.includes(':') ? m.kind.split(':').at(-1) : m.kind} · personal writing</p>
      <blockquote className="whitespace-pre-wrap border-l-2 pl-3">{m.text}</blockquote>
      <label className="flex items-center gap-2"><input type="checkbox" checked={ids.includes(m.id)} disabled={disabled || (!ids.includes(m.id) && ids.length >= 3)} onChange={e => onChange(e.target.checked ? [...ids, m.id] : ids.filter(id => id !== m.id))} />Use this earlier note for tutor context</label>
    </article>)}
    {error && <p role="status">{error}</p>}
  </section>
}
