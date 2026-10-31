import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'
import { usePreferences, useSetPreference } from '../preferences/api'

/** Optional starting aid; explicit save, independent of recap and mastery. */
export function NextStartCue({ editor = false }: { editor?: boolean }) {
  const prefs = usePreferences()
  const save = useSetPreference()
  const [edited, setEdited] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const stored = String(prefs.data?.values?.['session.next_start_cue'] ?? '')
  if (!editor)
    return stored ? (
      <aside
        aria-label="Next-start cue"
        className="border border-line rounded-md p-3 my-3 [overflow-wrap:anywhere]"
      >
        <p className="text-sm font-medium">Your next-start cue</p>
        <p>{stored}</p>
      </aside>
    ) : null
  const value = edited ?? stored
  return (
    <section aria-label="Next-start cue" className="my-4">
      <label htmlFor="next-start-cue" className="block text-sm font-medium">
        If-then starting cue (optional)
      </label>
      <p id="next-start-cue-help" className="text-sm text-muted">
        For example: “After I open the app, I recall one saved question.” Saved separately from your recap and
        shown on Home until you edit or clear it.
      </p>
      <Textarea
        id="next-start-cue"
        aria-describedby="next-start-cue-help"
        maxLength={300}
        value={value}
        disabled={save.isPending}
        onChange={(e) => {
          setEdited(e.target.value)
          setSaved(false)
        }}
      />
      {prefs.isError && (
        <p role="alert">
          The saved cue could not load. Your writing is kept here.{' '}
          <Button onClick={() => void prefs.refetch()}>Retry cue</Button>
        </p>
      )}
      <Button
        className="mt-2"
        disabled={!prefs.data || prefs.isError || save.isPending || edited === null}
        onClick={() =>
          void save
            .mutateAsync({ key: 'session.next_start_cue', value })
            .then(() => {
              setEdited(null)
              setSaved(true)
            })
            .catch(() => {
              /* Keep writing; display hook error. */
            })
        }
      >
        {save.isPending ? 'Saving cue…' : value ? 'Save next-start cue' : 'Clear next-start cue'}
      </Button>
      {save.isError && (
        <p role="alert">Could not save the cue. Your writing is kept. {(save.error as Error).message}</p>
      )}
      {saved && <p role="status">{stored ? 'Next-start cue saved for Home.' : 'Next-start cue cleared.'}</p>}
    </section>
  )
}
