import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { AnswerFollowup } from '../programs/AnswerFollowup'

/** Keep replies and save receipts mounted; deactivate streams when hidden. */
export function AssessmentDiscussion({
  answerId,
  sessionId,
  active,
}: {
  answerId: string | null | undefined
  sessionId: string
  active: boolean
}) {
  const [open, setOpen] = useState(false)
  const [started, setStarted] = useState(false)
  if (!answerId) return null
  return (
    <details
      className="mt-3"
      open={open}
      onToggle={(event) => {
        setOpen(event.currentTarget.open)
        if (event.currentTarget.open) setStarted(true)
      }}
    >
      <summary className="cursor-pointer font-medium">Discuss this feedback</summary>
      <p className="my-2 text-sm text-muted">
        Ask about your saved answer and feedback. This discussion does not change your score or progress.
        Closing it stops waiting and keeps your draft.
      </p>
      {started && (
        <>
          <RecordedAssessment answerId={answerId} />
          <AnswerFollowup answerId={answerId} expectedSessionId={sessionId} active={open && active} />
        </>
      )}
    </details>
  )
}

function RecordedAssessment({ answerId }: { answerId: string }) {
  const saved = useQuery({
    queryKey: ['answer', answerId],
    queryFn: ({ signal }) =>
      apiFetch<Schemas['AnswerDetail']>(`/api/answers/${encodeURIComponent(answerId)}`, { signal }),
    retry: false,
  })
  if (saved.isPending) return <p role="status">Loading your recorded answer…</p>
  if (saved.isError)
    return (
      <p role="alert">
        Could not load your recorded answer.{' '}
        <Button onClick={() => void saved.refetch()}>Retry recorded answer</Button>
      </p>
    )
  const record = saved.data
  if (!record || record.id !== answerId || record.surface !== 'assessment')
    return <p role="status">The original assessment record is unavailable.</p>
  const question = record.request.text
  const display = record.request.learner_answer_display
  return (
    <section
      aria-label="Your recorded assessment"
      className="my-3 border border-line rounded p-3 min-w-0 break-words"
    >
      <h3 className="font-medium">Your recorded answer</h3>
      <p className="text-sm text-muted">Original submitted work, separate from the tutor’s replies below.</p>
      <dl className="mt-2 grid gap-1">
        <dt className="font-medium">Question</dt>
        <dd className="whitespace-pre-wrap">
          {typeof question === 'string' && question.trim() ? question : 'Question text was not saved.'}
        </dd>
        <dt className="font-medium">You submitted</dt>
        <dd className="whitespace-pre-wrap">
          {typeof display === 'string' && display.trim()
            ? display
            : 'The displayed answer was not saved. Open saved feedback to review the available record.'}
        </dd>
      </dl>
    </section>
  )
}
