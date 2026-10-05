import { useState } from 'react'
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
        <AnswerFollowup answerId={answerId} expectedSessionId={sessionId} active={open && active} />
      )}
    </details>
  )
}
