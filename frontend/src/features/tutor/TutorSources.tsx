import { useRef, useState } from 'react'
import type { TurnDone } from '../../lib/api'
import { SourceViewer } from '../curriculum/SourceViewer'

import { withheldCount } from './sourceFlags'

export function TutorSources({ turn }: { turn: TurnDone }) {
  return <TurnSources key={turn.turn_id} turn={turn} />
}

function TurnSources({ turn }: { turn: TurnDone }) {
  const [selected, setSelected] = useState<string | null>(null)
  const trigger = useRef<HTMLButtonElement | null>(null)
  const source = turn.sources.find((item) => item.chunk_id === selected)
  const withheld = withheldCount(turn.dropped)
  return (
    <div className="text-sm mt-3">
      {turn.sources.length > 0 ? (
        <details>
          <summary className="cursor-pointer font-medium">Sources for this explanation</summary>
          <p className="text-muted my-2">
            Open a passage to compare it with the answer. A citation alone does not verify the explanation.
          </p>
          <ol className="list-decimal ml-5">
            {turn.sources.map((item) => (
              <li key={item.chunk_id}>
                <button
                  type="button"
                  className="underline text-left break-words"
                  aria-expanded={selected === item.chunk_id}
                  onClick={(event) => {
                    trigger.current = event.currentTarget
                    setSelected(item.chunk_id)
                  }}
                >
                  {item.citation}
                </button>
                {!item.cited && ' — not cited in the answer'}
                {(item.flagged ?? []).length > 0 && (
                  <span className="text-warn"> (flagged: {(item.flagged ?? []).join(', ')})</span>
                )}
              </li>
            ))}
          </ol>
          {source && (
            <SourceViewer
              key={source.chunk_id}
              chunkId={source.chunk_id}
              citation={source.citation}
              turnId={turn.turn_id}
              onClose={() => {
                setSelected(null)
                trigger.current?.focus()
              }}
            />
          )}
        </details>
      ) : (
        <p className="text-muted">No course source for this explanation.</p>
      )}
      {withheld > 0 && (
        <p className="text-muted mt-2">
          {withheld} source{withheld === 1 ? '' : 's'} withheld: flagged text from a web or untrusted tier was
          not sent to the tutor. You can inspect it under Corpus.
        </p>
      )}
    </div>
  )
}
