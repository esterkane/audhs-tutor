import { DisclosureSummary } from '../components/ui/disclosure'
import { Card, CardTitle } from '../components/ui/card'
import { useVocabDecks } from '../features/practice/api'
import { QuickAdd } from '../features/practice/VocabPanel'
import { VocabImport } from '../features/practice/VocabImport'
import { ListeningLessons } from '../features/listening/ListeningLessons'

export function Vocab() {
  const decks = useVocabDecks()
  const list = (decks.data?.decks ?? []) as Array<{ lang: string; title: string; cards: number; due: number }>
  return (
    <div className="grid gap-4">
      <ListeningLessons />
      <Card>
        <CardTitle as="h1">Vocabulary decks</CardTitle>
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
        <details className="mt-3 [&[open]>summary>svg]:rotate-90">
          <DisclosureSummary>Add one card</DisclosureSummary>
          <QuickAdd />
        </details>
      </Card>
      <details className="[&[open]>summary>svg]:rotate-90">
        <DisclosureSummary>Import a CSV list</DisclosureSummary>
        <VocabImport />
      </details>
    </div>
  )
}
