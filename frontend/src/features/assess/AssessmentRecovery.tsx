import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { ReadAloud } from '../voice/ReadAloud'
import { AssessmentSaveStatus } from '../programs/AssessmentSaveStatus'
import type { AttemptRequest, AttemptResult } from '../../lib/api'
import type { useAssessmentSubmission } from './useAssessmentSubmission'

type Recovery = ReturnType<typeof useAssessmentSubmission>['recovery']
export function AssessmentRecovery({
  recovery,
  onUse,
}: {
  recovery: Recovery
  onUse?: (result: AttemptResult, body: AttemptRequest) => boolean
}) {
  const [message, setMessage] = useState('')
  const [understood, setUnderstood] = useState(false)
  const { pending, lookup } = recovery
  if (!pending && !recovery.error && !recovery.memoryOnly) return null
  return (
    <section aria-label="Submission recovery" className="border border-warn rounded p-3 my-3 grid gap-2">
      <h3 className="font-semibold">Check your earlier submission</h3>
      {recovery.memoryOnly && (
        <p role="status">
          Recovery is kept in this page’s memory only. Reloading or closing the page loses the request
          identity. Keep saved feedback before leaving.
        </p>
      )}
      {recovery.error && (
        <>
          <p role="alert">{recovery.error}</p>
          {!recovery.memoryOnly && (
            <>
              <p>
                If storage is blocked or damaged, earlier request identities may be unavailable. An earlier
                attempt may already count; check Saved answers before submitting it as new.
              </p>
              <label>
                <input
                  type="checkbox"
                  checked={understood}
                  onChange={(event) => setUnderstood(event.target.checked)}
                />{' '}
                I understand an earlier attempt may already have been graded.
              </label>
              <Button disabled={!understood || recovery.checking} onClick={recovery.continueInMemory}>
                Continue in page memory only
              </Button>
            </>
          )}
        </>
      )}
      {!pending ? (
        <Button onClick={recovery.reload}>Retry reading recovery information</Button>
      ) : (
        <>
          <p>Your current work is kept separately. Checking retrieves a result; it does not grade again.</p>
          <details>
            <summary>Original question and submitted answer</summary>
            <p>{pending.question}</p>
            <pre className="whitespace-pre-wrap break-words">
              {pending.answerDisplay ?? pending.body.answer}
            </pre>
          </details>
          <Button disabled={recovery.checking} onClick={() => void recovery.check()}>
            {recovery.checking ? 'Checking…' : 'Check saved result'}
          </Button>
          {lookup?.status === 'unresolved' && (
            <p role="status">
              This submission is still running or was interrupted. It may already have changed your learning
              record. Keep checking or stop this session; do not submit it again as a new attempt.
            </p>
          )}
          {lookup?.status === 'not_found' && (
            <>
              <p>
                No request was found. You can send the original answer using the same recovery identity.
                Edited work will not be sent.
              </p>
              <Button disabled={recovery.checking} onClick={() => void recovery.resend()}>
                Send the original answer
              </Button>
            </>
          )}
          {lookup?.status === 'completed' && lookup.result && (
            <>
              <h4 className="font-semibold">Feedback on the original submission</h4>
              <p>{lookup.result.feedback}</p>
              <p>{lookup.result.next_step}</p>
              <ReadAloud
                text={`${pending.question}\n\n${lookup.result.feedback}\n\n${lookup.result.next_step}`}
              />
              <AssessmentSaveStatus key={lookup.result.attempt_id} result={lookup.result} />
              {onUse && (
                <Button
                  onClick={() => {
                    if (onUse(lookup.result!, pending.body)) recovery.clear()
                    else
                      setMessage(
                        'This feedback belongs to different work. Your current answer has not been replaced; open the saved feedback to review it.',
                      )
                  }}
                >
                  Use feedback for this answer
                </Button>
              )}
              <Button variant="ghost" onClick={recovery.clear}>
                Dismiss recovery and allow a new attempt
              </Button>
            </>
          )}
          {message && <p role="status">{message}</p>}
          <p className="text-sm text-muted">You can stop or change topic without completing recovery.</p>
        </>
      )}
    </section>
  )
}
