import { useRef } from 'react'
import { Markdown } from '../../components/Markdown'
import { Disclosure } from '../../components/ui/disclosure'

type Source = { chunk_id: string; citation: string; text: string; source_key?: string }

export function SourcedAnswer({ text, sources }: { text: string; sources: Source[] }) {
  const root = useRef<HTMLDivElement>(null)
  const origin = useRef<HTMLElement | null>(null)
  const keys = sources.map((source, index) => source.source_key ?? `S${index + 1}`)
  function openSource(key: string) {
    const index = keys.indexOf(key)
    if (index < 0) return
    origin.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    const details = root.current?.querySelector('details')
    if (details) details.open = true
    root.current?.querySelectorAll<HTMLHeadingElement>('h3[data-passage]')[index]?.focus()
  }
  return <div ref={root}>
    <Markdown text={text} sourceKeys={keys} onSourceReference={openSource} />
    {sources.length === 0 && <p className="text-warn">Source support unavailable — no passages were supplied for this answer.</p>}
    <Disclosure label={`Sources (${sources.length})`} className="mt-3">
      {sources.length === 0 && <p>Check this answer against your materials before relying on it.</p>}
      <p className="text-sm text-muted">Historical snapshots supplied to the model, not proof that every claim is supported.
        Select a source marker in the answer to read its passage. Review current source status on the saved-answer page.</p>
      {sources.map((source, index) => <section key={`${source.chunk_id}-${index}`} className="mt-3 border-t border-line pt-2">
        <h3 tabIndex={-1} data-passage={keys[index]} className="font-medium break-words">{source.citation}</h3>
        <p className="text-sm whitespace-pre-wrap break-words">{source.text}</p>
        <button type="button" className="text-accent underline rounded mt-2" onClick={() => {
          if (origin.current?.isConnected) origin.current.focus()
          else root.current?.querySelector<HTMLElement>('summary')?.focus()
        }}>Back to answer citation</button>
      </section>)}
    </Disclosure>
  </div>
}
