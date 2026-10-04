import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import type { useReviewSubmission } from './useReviewSubmission'

type Recovery = ReturnType<typeof useReviewSubmission>['recovery']
export function ReviewRecovery({
  recovery,
  onConfirmed,
  onRefresh,
}: {
  onRefresh?: (signal: AbortSignal) => Promise<void>
  recovery: Recovery
  onConfirmed: (itemId: string) => Promise<void>
}) {
  const [acknowledged, setAcknowledged] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const { pending, lookup } = recovery
  const [identity, setIdentity] = useState(pending?.id)
  if (identity !== pending?.id) {
    setIdentity(pending?.id)
    setApplying(false)
    setError('')
  }
  const refresh = useRef<AbortController | null>(null)
  useEffect(
    () => () => {
      refresh.current?.abort()
      refresh.current = null
    },
    [pending?.id],
  )
  async function refreshCard() {
    if (!onRefresh || refresh.current) return
    const controller = new AbortController()
    refresh.current = controller
    setApplying(true)
    setError('')
    let timer: ReturnType<typeof setTimeout> | undefined
    try {
      await Promise.race([
        onRefresh(controller.signal),
        new Promise<never>((_, reject) => {
          timer = setTimeout(() => {
            controller.abort()
            reject(new Error('The card could not be refreshed in time. Your earlier rating is kept.'))
          }, 15000)
        }),
      ])
      if (!controller.signal.aborted && refresh.current === controller) recovery.clear(pending?.id)
    } catch (cause) {
      if (refresh.current === controller) setError((cause as Error).message)
    } finally {
      clearTimeout(timer)
      if (refresh.current === controller) {
        refresh.current = null
        setApplying(false)
      }
    }
  }
  if (!pending && !recovery.previousRating && !recovery.error && !recovery.memoryOnly) return null
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
      {recovery.archivedRatings.map((previous) => (
        <details key={previous.id}>
          <summary>Previous card and rating — kept after refresh</summary>
          <p>{previous.question}</p>
          <p>
            Original choice: {['Again', 'Hard', 'Good', 'Easy'][previous.body.rating - 1]}. This rating was
            not applied to the updated card.
          </p>
          {previous.options && (
            <ul>
              {previous.options.map((option, i) => (
                <li key={i}>{option}</li>
              ))}
            </ul>
          )}
          {previous.reveal && <p>Original revealed answer: {previous.reveal}</p>}
          <Button onClick={() => recovery.dismissPrevious(previous.id)}>Dismiss previous rating</Button>
        </details>
      ))}
      {pending && (
        <>
          <p>{pending.question}</p>
          <p>
            Original choice: {['Again', 'Hard', 'Good', 'Easy'][pending.body.rating - 1]}
            {pending.body.hint_count ? ' (help used; this rating is capped at Hard)' : ''}.
          </p>
          {recovery.stale && (
            <>
              <p role="status">
                This card changed or its version could not be verified. This rating was not saved. Review the
                updated card and reveal its answer before choosing a new rating.
              </p>
              {onRefresh && (
                <Button disabled={recovery.checking || applying} onClick={() => void refreshCard()}>
                  {applying ? 'Refreshing card…' : 'Review updated card'}
                </Button>
              )}
            </>
          )}
          {!recovery.stale && (
            <Button disabled={recovery.checking || applying} onClick={() => void recovery.check()}>
              {recovery.checking ? 'Checking…' : 'Check saved rating'}
            </Button>
          )}
          {lookup?.status === 'unresolved' && (
            <p role="status">
              This rating is still running or was interrupted. Keep checking or stop; it will not be sent
              again automatically.
            </p>
          )}
          {!recovery.stale && lookup?.status === 'not_found' && (
            <>
              <p>
                No saved rating is visible yet. It may still be saving. Sending the original rating with the
                same identity will wait for or recover that result without applying it twice.
              </p>
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
