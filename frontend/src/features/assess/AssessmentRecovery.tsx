import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { ReadAloud } from '../voice/ReadAloud'
import { AssessmentSaveStatus } from '../programs/AssessmentSaveStatus'
import type { AttemptRequest, AttemptResult } from '../../lib/api'
import type { useAssessmentSubmission } from './useAssessmentSubmission'

type Recovery = ReturnType<typeof useAssessmentSubmission>['recovery']
export function AssessmentRecovery({
  recovery,
  onUse,
  onRefresh,
}: {
  recovery: Recovery
  onRefresh?: (signal: AbortSignal) => Promise<void>
  onUse?: (result: AttemptResult, body: AttemptRequest) => boolean
}) {
  const [message, setMessage] = useState('')
  const [understood, setUnderstood] = useState(false)
  const { pending, lookup } = recovery
  const [refreshing, setRefreshing] = useState(false)
  const refresh = useRef<AbortController | null>(null)
  const [identity, setIdentity] = useState(pending?.id)
  if (identity !== pending?.id) {
    setIdentity(pending?.id)
    setMessage('')
    setRefreshing(false)
  }
  useEffect(() => {
    return () => {
      refresh.current?.abort()
      refresh.current = null
    }
  }, [pending?.id])

  async function refreshQuestion() {
    if (!onRefresh || refresh.current) return
    const controller = new AbortController()
    refresh.current = controller
    setRefreshing(true)
    setMessage('')
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      await Promise.race([
        onRefresh(controller.signal),
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => {
            controller.abort()
            reject(new Error('The question could not be refreshed in time. Your answer is kept; try again.'))
          }, 15000)
        }),
      ])
      if (controller.signal.aborted || refresh.current !== controller) return
      recovery.clear()
    } catch (cause) {
      if (refresh.current === controller) setMessage((cause as Error).message)
    } finally {
      clearTimeout(timer)
      if (refresh.current === controller) {
        refresh.current = null
        setRefreshing(false)
      }
    }
  }
  if (!pending && !recovery.previousAnswer && !recovery.error && !recovery.memoryOnly) return null
  return (
    <section aria-label="Submission recovery" className="border border-warn rounded p-3 my-3 grid gap-2">
      <h3 className="font-semibold">
        {recovery.stale
          ? 'Review the updated question'
          : pending
            ? 'Check your earlier submission'
            : 'Your previous answer'}
      </h3>
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
      {recovery.previousAnswers.map((previous) => (
        <details key={previous.id}>
          <summary>Previous question and answer — kept after refresh</summary>
          <p>{previous.question}</p>
          <pre className="whitespace-pre-wrap break-words">
            {previous.answerDisplay ?? previous.body.answer}
          </pre>
          <p>
            This is your earlier answer, not a submission to the updated question. You can copy it into your
            current answer.
          </p>
          <Button variant="ghost" onClick={() => recovery.dismissPrevious(previous.id)}>
            Dismiss previous answer
          </Button>
        </details>
      ))}
      {!pending ? (
        recovery.error ? (
          <Button onClick={recovery.reload}>Retry reading recovery information</Button>
        ) : null
      ) : (
        <>
          {recovery.stale ? (
            <>
              <p role="status">
                This question changed or its version could not be verified. This submission was not graded.
                Your answer is kept below. Review the updated question before submitting again.
              </p>
              {onRefresh ? (
                <Button disabled={refreshing || recovery.checking} onClick={() => void refreshQuestion()}>
                  {refreshing ? 'Refreshing question…' : 'Review updated question — keep my answer'}
                </Button>
              ) : (
                <p>Reopen this activity to load its current question. Keep a copy of your answer first.</p>
              )}
            </>
          ) : (
            <p>Your current work is kept separately. Checking retrieves a result; it does not grade again.</p>
          )}
          <details>
            <summary>Original question and submitted answer</summary>
            <p>{pending.question}</p>
            <pre className="whitespace-pre-wrap break-words">
              {pending.answerDisplay ?? pending.body.answer}
            </pre>
          </details>
          {!recovery.stale && (
            <Button disabled={recovery.checking} onClick={() => void recovery.check()}>
              {recovery.checking ? 'Checking…' : 'Check saved result'}
            </Button>
          )}
          {lookup?.status === 'unresolved' && (
            <p role="status">
              This submission is still running or was interrupted. It may already have changed your learning
              record. Keep checking or stop this session; do not submit it again as a new attempt.
            </p>
          )}
          {!recovery.stale && lookup?.status === 'not_found' && (
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
