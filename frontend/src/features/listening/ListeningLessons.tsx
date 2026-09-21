import { useState } from 'react'
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
    <Card>
      <CardTitle>Guided listening</CardTitle>
      <p className="text-sm text-muted mb-2">
        One recording, one short clip at a time, one question each. Audio plays only when you press Play; a
        recording without an audio file is offered as a reading version. The lesson you pick here appears in
        the language block of a session.
      </p>
      {list.length === 0 ? (
        <p className="text-sm">
          No timed transcripts in the corpus yet. Ingest a lecture caption (.vtt/.srt) or a recording under
          Corpus.
        </p>
      ) : (
        <label className="text-sm font-medium">
          Lesson for the language block
          <select
            className="block border border-line rounded-md px-2 py-1 mt-1 max-w-full"
            value={selected}
            onChange={(e) => {
              setPending(e.target.value)
              setPref.mutate({ key: 'listening.document_id', value: e.target.value })
            }}
          >
            <option value="">none</option>
            {list.map((l) => (
              <option key={l.document_id} value={l.document_id}>
                {[l.course, l.lecture ?? l.title].filter(Boolean).join(' › ')} · {l.done}/{l.sections}{' '}
                answered
                {l.media_available ? '' : ' · no audio (reading version)'}
              </option>
            ))}
          </select>
        </label>
      )}
      {setPref.isError && (
        <p role="alert" className="text-sm text-warn mt-2">
          Not saved: {(setPref.error as Error).message}
        </p>
      )}
    </Card>
  )
}
