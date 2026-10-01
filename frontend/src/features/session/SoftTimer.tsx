import { useEffect, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'

/**
 * Soft timer: a wind-down prompt, never a cut-off. The deadline is derived from the *server's*
 * block start time plus the planned minutes plus any extension the learner asked for, so a reload
 * or a new block never inherits a stale deadline. Mount it with `key={blockKey}` so a new block
 * starts fresh. An accepted re-plan changes `plannedMin` and the deadline moves with it; "+5
 * minutes" is recorded on the server (`/api/plan/blocks/extend`) and arrives back as `extensionMin`,
 * which hides the prompt again because the deadline is now in the future.
 */
export function SoftTimer({
  blockKey,
  startedAt,
  plannedMin,
  extensionMin = 0,
  onExtend,
  onSaveStop,
  onFinishBlock,
  notify = false,
  pending = false,
}: {
  blockKey: string
  startedAt: string
  plannedMin: number
  extensionMin?: number
  onExtend: (minutes: number) => void
  onSaveStop: () => void
  onFinishBlock: () => void
  /** Browser notification when the wind-down prompt appears (preference ui.notifications). */
  notify?: boolean
  /** A transition is in flight: the three choices wait for it (no double posts). */
  pending?: boolean
}) {
  const started = Date.parse(startedAt)
  const deadline = started + (plannedMin + extensionMin) * 60_000
  // `now` is external state (the clock) sampled by a subscription, never read during render.
  const [now, setNow] = useState<number | null>(null)
  useEffect(() => {
    const tick = () => setNow(Date.now())
    const first = setTimeout(tick, 0)
    const id = setInterval(tick, 5_000)
    return () => {
      clearTimeout(first)
      clearInterval(id)
    }
  }, [blockKey])
  const show = !Number.isNaN(started) && now != null && now >= deadline
  useEffect(() => {
    if (!show || !notify) return
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      new Notification('Planned time is up', { body: 'Save & stop, 5 more minutes, or finish the block.' })
    }
  }, [show, notify])
  if (!show) return null
  return (
    <Card role="status" className="border-warn mb-4">
      <p className="mb-2">
        Planned time is up ({plannedMin + extensionMin} min
        {extensionMin ? `, incl. ${extensionMin} extra` : ''}). Which next?
      </p>
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" onClick={onSaveStop} disabled={pending}>
          Save &amp; stop
        </Button>
        <Button onClick={() => onExtend(5)} disabled={pending}>
          5 more minutes
        </Button>
        <Button onClick={onFinishBlock} disabled={pending}>
          Finish this block
        </Button>
      </div>
    </Card>
  )
}
