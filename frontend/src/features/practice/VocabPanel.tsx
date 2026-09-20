import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useRate } from '../review/api'
import { useAddVocab, useDueLanguage } from './api'

const RATINGS = [
  { value: 1, label: 'Again' },
  { value: 2, label: 'Hard' },
  { value: 3, label: 'Good' },
  { value: 4, label: 'Easy' },
]

/** The language block: due vocabulary cards on the same FSRS scheduler, one at a time. */
export function VocabPanel({ sessionId, onDone }: { sessionId: string; onDone: () => void }) {
  const due = useDueLanguage(sessionId)
  const rate = useRate()
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const items = due.data?.items ?? []
  const item = items[idx]

  async function rateIt(rating: number) {
    if (!item) return
    await rate.mutateAsync({ itemId: item.item_id, body: { session_id: sessionId, rating } })
    setRevealed(false)
    setIdx(idx + 1)
  }

  return (
    <Card>
      <CardTitle>Vocabulary</CardTitle>
      {due.isLoading && <p>Loading cards…</p>}
      {due.data && !item && (
        <div>
          <p className="text-sm">
            {items.length === 0 ? 'No cards are due.' : `${items.length} cards reviewed.`}
          </p>
          <Button variant="primary" className="mt-3" onClick={onDone}>
            Continue
          </Button>
        </div>
      )}
      {item && (
        <div>
          <p className="text-sm text-muted">
            {item.skill_title} · card {idx + 1} of {items.length}
          </p>
          <p className="text-2xl mt-2">{item.question}</p>
          {!revealed ? (
            <Button className="mt-3" onClick={() => setRevealed(true)}>
              Show translation
            </Button>
          ) : (
            <div className="mt-3">
              <p className="text-lg">{item.reveal}</p>
              <div
                className="flex flex-wrap gap-2 mt-3"
                role="group"
                aria-label="How well did you recall it?"
              >
                {RATINGS.map((r) => (
                  <Button key={r.value} disabled={rate.isPending} onClick={() => void rateIt(r.value)}>
                    {r.label}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <details className="mt-4">
        <summary className="cursor-pointer text-sm font-medium">Add a card</summary>
        <QuickAdd />
      </details>
    </Card>
  )
}

export function QuickAdd() {
  const add = useAddVocab()
  const [lang, setLang] = useState('de')
  const [word, setWord] = useState('')
  const [translation, setTranslation] = useState('')
  return (
    <form
      className="mt-4 flex flex-wrap gap-2 items-end"
      onSubmit={(e) => {
        e.preventDefault()
        add.mutate({ lang, word, translation, example: null })
        setWord('')
        setTranslation('')
      }}
    >
      <label className="text-sm font-medium">
        Language
        <input
          className="block w-16 border border-line rounded-md px-2 py-1 mt-1"
          value={lang}
          onChange={(e) => setLang(e.target.value)}
        />
      </label>
      <label className="text-sm font-medium grow">
        Word
        <input
          className="block w-full border border-line rounded-md px-2 py-1 mt-1"
          value={word}
          onChange={(e) => setWord(e.target.value)}
        />
      </label>
      <label className="text-sm font-medium grow">
        Translation
        <input
          className="block w-full border border-line rounded-md px-2 py-1 mt-1"
          value={translation}
          onChange={(e) => setTranslation(e.target.value)}
        />
      </label>
      <Button type="submit" size="sm" disabled={!word || !translation || add.isPending}>
        Add card
      </Button>
      {add.isSuccess && (
        <span role="status" className="text-sm text-muted">
          Added.
        </span>
      )}
    </form>
  )
}
