export function TransitionWaitNotice({ visible }: { visible: boolean }) {
  if (!visible) return null
  return (
    <p role="status" className="text-sm text-muted mt-2">
      This change is taking longer than expected. The server may still be processing it. You can use
      Pause and return Home. The change will not be retried automatically.
    </p>
  )
}
