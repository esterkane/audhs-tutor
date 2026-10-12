import { useState } from 'react'
import { Disclosure } from '../../components/ui/disclosure'
import { references, suggestedReferences } from './referenceCatalog'

export function FurtherReading({ question }: { question: string }) {
  const [topic, setTopic] = useState('suggested')
  const cards =
    topic === 'suggested' ? suggestedReferences(question) : references.filter((card) => card.id === topic)
  return (
    <Disclosure label="Further reading · official documentation" className="mt-4">
      <p className="text-sm text-muted mb-3">
        Optional reading, not evidence used to check this answer. Suggestions are matched locally; opening a
        link visits an external website in a new tab.
      </p>
      <label className="block mb-2">
        Documentation topic
        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="block w-full border border-line rounded-panel bg-card p-2 mt-1"
        >
          <option value="suggested">Related to this question</option>
          {references.map((card) => (
            <option key={card.id} value={card.id}>
              {card.title}
            </option>
          ))}
        </select>
      </label>
      {!cards.length && (
        <p>No reviewed link matches yet. You can browse one of the available documentation topics above.</p>
      )}
      <div className="space-y-3 mt-3">
        {cards.map((card) => (
          <article key={card.id} className="border border-line rounded-panel p-3 space-y-2">
            <h3 className="font-semibold">
              <a href={card.url} target="_blank" rel="noopener noreferrer" referrerPolicy="no-referrer">
                {card.title} (external)
              </a>
            </h3>
            <p className="text-sm">
              {card.publisher} · Accessible without sign-in when inspected on {card.inspectedAt}.
            </p>
            <p>{card.why}</p>
            <p className="text-sm text-muted">{card.versionNote}</p>
            <details>
              <summary>Source and reuse information</summary>
              <p className="text-sm mt-2">{card.reuseNote}</p>
            </details>
          </article>
        ))}
      </div>
      <p className="text-sm text-muted mt-3">
        Link metadata is available offline. The external documentation needs a connection unless you already
        saved a local copy.
      </p>
    </Disclosure>
  )
}
