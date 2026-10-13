import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Disclosure } from '../../components/ui/disclosure'
import { useSavedReading } from '../representations/api'
import { LessonReader } from './LessonReader'


export function SavedLessonReading({ reading, active, hasReply }: {
  reading: ReturnType<typeof useSavedReading>
  active: boolean
  hasReply: boolean
}) {
  const [open, setOpen] = useState(!hasReply)
  const failure = reading.isError && <div><p role="alert">Could not refresh saved lesson text. Any text below is the last loaded version.</p><Button onClick={() => void reading.refetch()}>Retry saved lesson</Button></div>
  if (!reading.data && failure) return <Card>{failure}</Card>
  if (!reading.data) return reading.isFetching ? <p role="status">Checking for saved lesson text…</p> : null
  const saved = reading.data
  const text = saved.passages.map((passage, index) => `## ${index === 0 ? 'Explanation' : `Worked example ${index}`}\n\n${passage}`).join('\n\n')
  return <Card>
    <CardTitle>Saved explanation</CardTitle>
    {failure}
    <Disclosure label="Saved lesson text" open={!hasReply} onToggle={event => setOpen(event.currentTarget.open)}>
      <p className="text-sm text-muted mb-3">Saved locally · lesson version {saved.object_version}. No new answer was generated. Saving and activation do not verify accuracy or mark the questions reviewed.</p>
      <LessonReader key={saved.content_sha256} identity={`saved-lesson:${saved.object_id}:${saved.content_sha256}`} text={text} active={active && open} sources={saved.source_ids.map(id => ({ chunk_id: id, citation: 'Linked source passage', cited: false }))} />
      <Disclosure label="Lesson origin and sources" className="mt-3">
        <p className="text-sm">This is the current saved lesson text. The original answer and draft may differ after edits.</p>
        <div className="flex flex-wrap gap-3">
          <Link className="underline" to={`/curriculum?draft=${encodeURIComponent(saved.draft_id)}`}>Review lesson draft</Link>
          <Link className="underline" to={`/answers/${encodeURIComponent(saved.answer_id)}`}>Original saved answer</Link>
        </div>
        {!saved.source_ids.length && <p className="text-sm">No source passages are linked to this lesson text.</p>}
      </Disclosure>
    </Disclosure>
  </Card>
}
