import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { usePreferences, useSetPreference } from '../preferences/api'
import { useListeningLessons } from './api'

/**
 * Pick the recording the language block offers as guided listening. Lessons come from the corpus
 * (an ingested caption/transcript with timestamps); audio is available only when the media file sits
 * next to it under the ingest roots — otherwise the transcript is offered as a reading version.
 */
export function ListeningLessons() {
  const lessons = useListeningLessons()
  const prefs = usePreferences()
  const setPref = useSetPreference()
  const saved = String(
    (prefs.data?.values as Record<string, unknown> | undefined)?.['listening.document_id'] ?? '',
  )
  const [pending, setPending] = useState<string | null>(null)
  const selected = setPref.isPending && pending != null ? pending : saved
  const list = lessons.data?.lessons ?? []
  return (
    <Card className="min-w-0">
      <CardTitle>Guided listening</CardTitle>
      <p className="text-sm text-muted mb-2">
        One recording, one short clip at a time, one question each. Audio plays only when you press Play; a
        recording without an audio file is offered as a reading version. The lesson you pick here appears in
        the language block of a session.
      </p>
      <Button variant="ghost" size="sm" aria-disabled={lessons.isFetching} aria-busy={lessons.isFetching}
        onClick={() => { if (!lessons.isFetching) void lessons.refetch() }}>
        {lessons.isError ? 'Retry recordings' : 'Refresh recordings'}
      </Button>
      {lessons.isPending && <p role="status">Loading recordings…</p>}
      {lessons.isError && <p role={lessons.data ? 'status' : 'alert'}>
        {lessons.data ? 'Could not refresh recordings. The last loaded list is kept.' : 'Could not load recordings.'} {lessons.error.message}
      </p>}
      {prefs.isPending && <p role="status">Loading your saved listening choice…</p>}
      {prefs.isError && <div>
        <p role="alert">Could not load your listening choice. Retry before changing it. {prefs.error.message}</p>
        <Button variant="ghost" size="sm" aria-disabled={prefs.isFetching} aria-busy={prefs.isFetching}
          onClick={() => { if (!prefs.isFetching) void prefs.refetch() }}>Retry listening choice</Button>
      </div>}
      {lessons.data && (list.length === 0 ? (
        <p className="text-sm">
          {lessons.isError ? 'No timed transcripts in the last loaded list.' : 'No timed transcripts in the corpus yet. Ingest a lecture caption (.vtt/.srt) or a recording under Corpus.'}
        </p>
      ) : (
        <label className="text-sm font-medium">
          Lesson for the language block
          <select
            className="block w-full min-w-0 min-h-control-target border border-control rounded-md px-2 py-1 mt-1 max-w-full"
            disabled={!prefs.data || prefs.isError || setPref.isPending}
            value={selected}
            onChange={(e) => {
              setPending(e.target.value)
              setPref.mutate({ key: 'listening.document_id', value: e.target.value })
            }}
          >
            <option value="">{prefs.data ? 'none' : 'Listening choice unavailable'}</option>
            {selected && !list.some(l => l.document_id === selected) &&
              <option value={selected}>Saved recording is not in this list</option>}
            {list.map((l) => (
              <option key={l.document_id} value={l.document_id}>
                {[l.course, l.lecture ?? l.title].filter(Boolean).join(' › ')} · {l.done}/{l.sections}{' '}
                answered
                {l.media_available ? '' : ' · no audio (reading version)'}
              </option>
            ))}
          </select>
        </label>
      ))}
      {setPref.isPending && <p role="status">Saving listening choice…</p>}
      {setPref.isSuccess && <p role="status">Listening choice saved.</p>}
      {setPref.isError && (
        <p role="alert" className="text-sm text-warn mt-2">
          Could not confirm the listening choice was saved: {(setPref.error as Error).message}
        </p>
      )}
    </Card>
  )
}
