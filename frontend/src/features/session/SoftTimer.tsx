import { useEffect, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'

/** Soft timer: a wind-down prompt, never a cut-off. */
export function SoftTimer({
  minutes,
  onSaveStop,
  onFinishBlock,
}: {
  minutes: number
  onSaveStop: () => void
  onFinishBlock: () => void
}) {
  const [deadline, setDeadline] = useState(() => Date.now() + minutes * 60_000)
  const [show, setShow] = useState(false)
  useEffect(() => {
    const id = setInterval(() => {
      if (Date.now() >= deadline) setShow(true)
    }, 5_000)
    return () => clearInterval(id)
  }, [deadline])
  if (!show) return null
  return (
    <Card role="status" className="border-warn mb-4">
      <p className="mb-2">Planned time is up ({minutes} min). Which next?</p>
      <div className="flex gap-2 flex-wrap">
        <Button variant="primary" onClick={onSaveStop}>
          Save &amp; stop
        </Button>
        <Button
          onClick={() => {
            setDeadline(Date.now() + 5 * 60_000)
            setShow(false)
          }}
        >
          5 more minutes
        </Button>
        <Button
          onClick={() => {
            setShow(false)
            onFinishBlock()
          }}
        >
          Finish this block
        </Button>
      </div>
    </Card>
  )
}
