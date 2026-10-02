import { useRef, useState } from 'react'
import { SourceViewer } from '../curriculum/SourceViewer'
import type { RenderOut } from './api'

export function RepresentationSources({
  value,
}: {
  value: Pick<RenderOut, 'provenance_available' | 'source_snapshot'>
}) {
  const [selected, setSelected] = useState<{ id: string; citation: string } | null>(null)
  const sources = value.source_snapshot ?? []
  const trigger = useRef<HTMLButtonElement | null>(null)
  if (!value.provenance_available)
    return (
      <p className="text-sm text-muted mt-2">
        Original source details were not recorded for this cached explanation. Its citations cannot be
        reconstructed reliably.
      </p>
    )
  return (
    <div className="mt-2 text-sm">
      <details>
        <summary>Source context used for this explanation</summary>
        <p>
          These labels were recorded when the explanation was generated. They do not verify its claims.
          Opening a passage shows the current local copy, which may have changed.
        </p>
        {sources.length === 0 ? (
          <p>No source passages were supplied.</p>
        ) : (
          <ul>
            {sources.map((source, index) => (
              <li key={source.chunk_id}>
                <button
                  className="underline text-left"
                  onClick={(event) => {
                    trigger.current = event.currentTarget
                    setSelected({ id: source.chunk_id, citation: source.citation })
                  }}
                >
                  [{index + 1}] {source.citation}
                </button>
                {!source.cited && <span> — supplied context, not cited in the explanation</span>}
                {(source.flagged ?? []).length > 0 && (
                  <p>Source warning: {(source.flagged ?? []).join(', ')}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </details>
      {selected && (
        <SourceViewer
          chunkId={selected.id}
          citation={selected.citation}
          onClose={() => {
            setSelected(null)
            trigger.current?.focus()
          }}
        />
      )}
    </div>
  )
}
