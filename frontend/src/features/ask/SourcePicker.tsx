import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { apiFetch, type Schemas } from '../../lib/api'
import { previousPassages, type SelectablePassage, useSelectedPassages } from './useSelectedPassages'


export function SourcePicker({
  selection,
  disabled,
  previousSources,
}: {
  selection: ReturnType<typeof useSelectedPassages>
  disabled: boolean
  previousSources?: unknown
}) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SelectablePassage[]>([])
  const [historical, setHistorical] = useState(false)
  const previous = previousPassages(previousSources)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const active = useRef<AbortController | null>(null)
  useEffect(() => () => active.current?.abort(), [])
  async function search() {
    if (active.current || disabled || !query.trim()) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    setHits([])
    setHistorical(false)
    setSearched(false)
    try {
      const result = await apiFetch<Schemas['SearchOut']>('/api/corpus/search', {
        method: 'POST',
        body: JSON.stringify({ query: query.trim(), k: 6, tutor_view: true }),
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      setHits(result.hits)
      setSearched(true)
    } catch (e) {
      if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Source search failed.')
    } finally {
      if (active.current === controller) {
        active.current = null
        setBusy(false)
      }
    }
  }
  return (
    <Disclosure
      label={`Attach local sources (optional)${selection.selected.length ? ` · ${selection.selected.length} selected` : ''}`}
    >
      <p className="text-sm text-muted">
        Choose up to six passages for this reply. They stay local. Prior replies remain conversation context;
        their sources are not automatically attached.
      </p>
      {previous === null && <p role="status">Previous passage snapshots are unreadable. Search the local library to select sources again.</p>}
      {!!previous?.length && <Button type="button" disabled={disabled || busy}
        onClick={() => { setHits(previous); setHistorical(true); setSearched(false); setError('') }}>
        Review previous passages
      </Button>}
      {historical && <p role="status" className="text-sm text-muted">Saved snapshots from the previous reply. Select passages to attach them; nothing is attached automatically. Availability, text changes and source trust are checked when you send.</p>}
      {selection.invalid && (
        <p role="alert">
          Saved source selection is unreadable.{' '}
          <Button type="button" disabled={disabled} onClick={() => selection.set([])}>
            Clear unreadable selection
          </Button>
        </p>
      )}
      {selection.error && <p role="alert">{selection.error}</p>}
      <label htmlFor="ask-source-query" className="block mt-3">
        Find passages in your local library
      </label>
      <input
        id="ask-source-query"
        value={query}
        maxLength={500}
        disabled={disabled || busy}
        className="w-full rounded border border-line bg-card p-2"
        onChange={(e) => {
          setQuery(e.target.value)
          setHits([])
          setHistorical(false)
          setSearched(false)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault()
            void search()
          }
        }}
      />
      <Button type="button" disabled={disabled || busy || !query.trim()} onClick={() => void search()}>
        {busy ? 'Searching locally…' : 'Find passages'}
      </Button>
      {error && <p role="alert">{error} Your selected passages are kept.</p>}
      {searched && !hits.length && (
        <p role="status">No passages found. Try other words, or ask without sources.</p>
      )}
      <div className="space-y-3 mt-3">
        {hits.map((hit) => {
          const checked = selection.selected.some((s) => s.chunk_id === hit.chunk_id)
          return (
            <div key={hit.chunk_id} className="border border-line rounded-panel p-3">
              <label className="flex gap-2 items-start">
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={disabled || hit.quarantined || (!checked && selection.selected.length >= 6)}
                  onChange={(e) =>
                    selection.set(
                      e.target.checked
                        ? [...selection.selected, hit]
                        : selection.selected.filter((s) => s.chunk_id !== hit.chunk_id),
                    )
                  }
                />
                <span className="break-words">{hit.citation}</span>
              </label>
              <p className="text-sm whitespace-pre-wrap break-words mt-2">{hit.text}</p>
            </div>
          )
        })}
      </div>
      {selection.selected.length > 0 && (
        <section aria-label="Passages attached to this question" className="space-y-2 mt-3">
          {selection.selected.map((hit) => (
            <div key={hit.chunk_id} className="border border-line rounded-panel p-3">
              <p className="font-medium break-words">{hit.citation}</p>
              <p className="text-sm whitespace-pre-wrap break-words">{hit.text}</p>
              <Button
                type="button"
                disabled={disabled}
                onClick={() => selection.set(selection.selected.filter((s) => s.chunk_id !== hit.chunk_id))}
              >
                Remove {hit.citation}
              </Button>
            </div>
          ))}
        </section>
      )}
    </Disclosure>
  )
}
