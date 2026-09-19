import * as Dialog from '@radix-ui/react-dialog'
import { useState } from 'react'
import { api } from '../lib/api'
import { useMode } from '../stores/mode'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'

/** Always visible in the shell. Capture in ≤ 2 interactions: open, type + Enter. */
export function ParkingLotButton() {
  const { sessionId, skillId } = useMode()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [status, setStatus] = useState<string | null>(null)

  async function submit() {
    if (!text.trim()) return
    await api.park({
      session_id: sessionId,
      text: text.trim(),
      node_id: skillId,
    })
    setText('')
    setStatus('Parked. It stays out of the way until you promote it.')
    setOpen(false)
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button
          variant="outline"
          className="fixed bottom-4 right-4 shadow-md bg-card"
          aria-label="Parking lot: park a tangent for later"
          title="Park a tangent for later"
        >
          🅿 Park
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content
          className="fixed left-1/2 top-1/3 w-[min(90vw,32rem)] -translate-x-1/2 rounded-lg bg-card p-4 shadow-lg border border-line"
          aria-describedby="park-desc"
        >
          <Dialog.Title className="text-lg font-semibold">Park a tangent</Dialog.Title>
          <Dialog.Description id="park-desc" className="text-sm text-muted mb-2">
            One line. Enter to park. It is linked to the current skill.
          </Dialog.Description>
          <Textarea
            autoFocus
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void submit()
              }
            }}
            aria-label="Tangent to park"
            className="min-h-16"
          />
          <div className="flex gap-2 justify-end mt-2">
            <Dialog.Close asChild>
              <Button variant="ghost">Cancel</Button>
            </Dialog.Close>
            <Button variant="primary" onClick={() => void submit()} disabled={!text.trim()}>
              Park it
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
      {status && (
        <p
          role="status"
          className="fixed bottom-16 right-4 rounded-md bg-card border border-line px-3 py-2 text-sm shadow"
        >
          {status}
        </p>
      )}
    </Dialog.Root>
  )
}
