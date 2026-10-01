import { WaitingElapsed } from './WaitingElapsed'

export type ResponseStatus = 'idle' | 'streaming' | 'complete' | 'partial' | 'stopped' | 'failed'

/** Announce state transitions, never tokens or timer ticks. */
export function TutorResponseStatus({
  status,
  startedAt,
}: {
  status: ResponseStatus
  startedAt: number | null
}) {
  const message = {
    idle: '',
    streaming: 'Tutor is preparing a response…',
    complete: 'Tutor response ready.',
    partial: 'Response interrupted. The text received so far is kept.',
    stopped: 'Response stopped. Your draft and any received text are kept.',
    failed: '', // The caller provides the actionable error in an alert.
  }[status]
  return (
    <>
      <p role="status" aria-label="Tutor response status" aria-atomic="true" className="text-sm mt-2">
        {message}
      </p>
      {status === 'streaming' && startedAt !== null && (
        <WaitingElapsed key={startedAt} startedAt={startedAt} />
      )}
    </>
  )
}
