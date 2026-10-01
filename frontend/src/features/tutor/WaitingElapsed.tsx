import { useEffect, useState } from 'react'

/** Elapsed time only: a quiet display, never a completion estimate or live announcement. */
export function WaitingElapsed({ startedAt }: { startedAt: number }) {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const update = () => setSeconds(Math.max(0, Math.floor((performance.now() - startedAt) / 1000)))
    const timer = setInterval(update, 1000)
    document.addEventListener('visibilitychange', update)
    return () => {
      clearInterval(timer)
      document.removeEventListener('visibilitychange', update)
    }
  }, [startedAt])
  return (
    <p aria-live="off" className="text-sm text-muted">
      Waiting {seconds} {seconds === 1 ? 'second' : 'seconds'}. You can keep writing or stop this response.
    </p>
  )
}
