import { Card, CardTitle } from '../components/ui/card'
import { useVocabDecks } from '../features/practice/api'
import { QuickAdd } from '../features/practice/VocabPanel'

export function Vocab() {
  const decks = useVocabDecks()
  const list = (decks.data?.decks ?? []) as Array<{ lang: string; title: string; cards: number; due: number }>
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Vocabulary decks</CardTitle>
        <p className="text-sm text-muted mb-2">
          Cards are spaced like everything else. They appear only in the language block of a session (switch
          on "Plan a language block" under Preferences).
        </p>
        {list.length === 0 ? (
          <p className="text-sm">No decks yet. Add a first card below.</p>
        ) : (
          <ul className="text-sm grid gap-1">
            {list.map((d) => (
              <li key={d.lang}>
                {d.title}: {d.cards} cards · {d.due} due
              </li>
            ))}
          </ul>
        )}
        <QuickAdd />
      </Card>
    </div>
  )
}
