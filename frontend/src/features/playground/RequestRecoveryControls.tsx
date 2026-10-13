import { Button } from '../../components/ui/button'

export function RequestRecoveryControls({
  recovery,
  busy,
  retry,
  originalContext = 'answer, code and material',
  saveOnly = false,
  savedAction = 'save another review',
}: {
  recovery: {
    pending: { view: { display: string } } | null
    error: string
    needsDiscard: boolean
    canUseMemoryOnly: boolean
    discard: () => void
    continueInMemory: () => void
  }
  originalContext?: string
  saveOnly?: boolean
  savedAction?: string
  busy: boolean
  retry: () => void
}) {
  return (
    <>
      {recovery.error && <p role="alert">{recovery.error}</p>}
      {!busy && (recovery.pending || recovery.needsDiscard || recovery.canUseMemoryOnly) && (
        <section aria-label="Recover tutor request" className="border border-border rounded p-3 my-3">
          <p>
            {recovery.pending
              ? 'No result has been confirmed for the previous request in this tab.'
              : 'Saved retry details need attention.'}
          </p>
          {recovery.pending && (
            <>
              <p className="text-sm">{recovery.pending.view.display.slice(0, 300)}</p>
              <Button onClick={retry}>Retry previous request</Button>
            </>
          )}
          <p className="text-sm text-muted">
            Retry uses the original {originalContext}. Your later edits are not sent. It can recover a
            completed result without {saveOnly ? 'saving it twice' : 'generating again'}. An interrupted request may remain unavailable.
          </p>
          <details>
            <summary>Start different work</summary>
            <p>
              The previous request may still finish. Discarding its retry lets your next send start a new
              request and may {saveOnly ? savedAction : 'cause another model call'}.
            </p>
            <Button onClick={() => recovery.discard()}>Discard retry and start new</Button>
          </details>
          {recovery.canUseMemoryOnly && (
            <>
              <p>
                Storage is unavailable. Continuing without reload recovery may {saveOnly ? savedAction : 'start another model call'}; an
                earlier request may still finish.
              </p>
              <Button onClick={recovery.continueInMemory}>Continue without reload recovery</Button>
            </>
          )}
        </section>
      )}
    </>
  )
}
