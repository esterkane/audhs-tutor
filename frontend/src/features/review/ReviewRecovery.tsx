import { useState } from 'react'
import { Button } from '../../components/ui/button'
import type { useReviewSubmission } from './useReviewSubmission'

type Recovery = ReturnType<typeof useReviewSubmission>['recovery']
export function ReviewRecovery({
  recovery,
  onConfirmed,
}: {
  recovery: Recovery
  onConfirmed: (itemId: string) => Promise<void>
}) {
  const [acknowledged, setAcknowledged] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const { pending, lookup } = recovery
  if (!pending && !recovery.error && !recovery.memoryOnly) return null
  return (
    <section aria-label="Review submission recovery" className="border border-warn rounded p-3 grid gap-2">
      <h3 className="font-semibold">Check your earlier rating</h3>
      {recovery.memoryOnly && (
        <p role="status">
          Recovery is in page memory only. Reloading or closing this page loses its identity and review queue.
        </p>
      )}
      {recovery.error && <p role="alert">{recovery.error}</p>}
      {recovery.storageError && !recovery.memoryOnly && (
        <>
          <p>
            Blocked or damaged storage may hide an earlier rating that already counted. Continuing without its
            identity can repeat that review.
          </p>
          <label>
            <input
              type="checkbox"
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
            />{' '}
            I understand an earlier rating may already have been saved.
          </label>
          <Button disabled={!acknowledged || recovery.checking} onClick={recovery.continueInMemory}>
            Continue in page memory only
          </Button>
        </>
      )}
      {!pending && recovery.error && (
        <Button onClick={recovery.reload}>Retry reading recovery information</Button>
      )}
      {pending && (
        <>
          <p>{pending.question}</p>
          <p>
            Original choice: {['Again', 'Hard', 'Good', 'Easy'][pending.body.rating - 1]}
            {pending.body.hint_count ? ' (help used; this rating is capped at Hard)' : ''}.
          </p>
          <Button disabled={recovery.checking || applying} onClick={() => void recovery.check()}>
            {recovery.checking ? 'Checking…' : 'Check saved rating'}
          </Button>
          {lookup?.status === 'unresolved' && (
            <p role="status">
              This rating is still running or was interrupted. Keep checking or stop; it will not be sent
              again automatically.
            </p>
          )}
          {lookup?.status === 'not_found' && (
            <>
              <p>No request was found. You can send the original rating with the same identity.</p>
              <Button disabled={recovery.checking || applying} onClick={() => void recovery.resend()}>
                Send original rating
              </Button>
            </>
          )}
          {lookup?.status === 'completed' && lookup.result && (
            <>
              <p role="status">
                The original rating was saved. Its recorded schedule is historical; updating the queue loads
                what is due now.
              </p>
              <Button
                disabled={recovery.checking || applying}
                onClick={() => {
                  setApplying(true)
                  setError('')
                  void onConfirmed(pending.itemId)
                    .then(() => recovery.clear())
                    .catch((cause: Error) => setError(cause.message))
                    .finally(() => setApplying(false))
                }}
              >
                {applying ? 'Updating…' : 'Update review queue'}
              </Button>
            </>
          )}
        </>
      )}
      {error && <p role="alert">{error}</p>}
      <p className="text-sm text-muted">You can stop or change activity without completing recovery.</p>
    </section>
  )
}
