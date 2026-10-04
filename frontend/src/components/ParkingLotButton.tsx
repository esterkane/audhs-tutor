import * as Dialog from '@radix-ui/react-dialog'
import { useEffect, useRef, useState } from 'react'
import { api } from '../lib/api'
import { useThoughtDraft } from '../features/parking/draft'
import { ParkedList } from '../features/parking/ParkedList'
import { useParkingActions } from '../features/parking/api'
import { useMode } from '../stores/mode'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'

/** Always available in the shell header. Capture in ≤ 2 interactions: open, type + Enter. */
export function ParkingLotButton() {
  const { sessionId, skillId } = useMode()
  const [open, setOpen] = useState(false)
  const { draft, update: updateDraft, storageError } = useThoughtDraft()
  const text = draft.text
  const pending = useRef<AbortController | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const { invalidate } = useParkingActions()

  useEffect(() => () => { pending.current?.abort(); pending.current = null }, [])

  async function submit() {
    if (!text.trim() || pending.current) return
    const controller = new AbortController()
    pending.current = controller
    let timer: ReturnType<typeof setTimeout> | undefined
    updateDraft({ ...draft, unconfirmed: true })
    setSaving(true)
    setError('')
    setStatus(null)
    try {
      await Promise.race([
        api.park({ session_id: draft.sessionId, text: text.trim(), node_id: draft.skillId }, controller.signal),
        new Promise<never>((_, reject) => { timer = setTimeout(() => { controller.abort(); reject(new Error('Save wait timed out')) }, 15000) }),
      ])
      if (pending.current !== controller) return
      updateDraft({ text: '', sessionId: null, skillId: null, unconfirmed: false })
      invalidate()
      setStatus('Thought saved. Open Save for later to find it under Saved thoughts.')
      setOpen(false)
    } catch {
      if (pending.current !== controller) return
      invalidate()
      setError('Could not confirm the save. Your text is still here. Check Saved thoughts before trying again; the server may have saved it.')
    } finally {
      clearTimeout(timer)
      if (pending.current === controller) { pending.current = null; setSaving(false) }
    }
  }

  return (
    <div className="grid gap-2 min-w-0 max-w-full">
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>
        <Button
          variant="outline"
          className="bg-card"
          aria-label="Save for later"
          title="Save a thought for later"
        >
          Save for later
        </Button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/30" />
        <Dialog.Content
          className="fixed left-1/2 top-4 max-h-[calc(100dvh-2rem)] overflow-y-auto w-[min(90vw,32rem)] -translate-x-1/2 rounded-lg bg-card p-4 shadow-lg border border-line"
          aria-describedby="park-desc"
        >
          <Dialog.Title className="text-lg font-semibold">Save a thought for later</Dialog.Title>
          <Dialog.Description id="park-desc" className="text-sm text-muted mb-2">
            Save an idea without leaving your work. Press Enter to save or Shift+Enter for a new line. Session and skill context are included when available.
          </Dialog.Description>
          <Textarea
            autoFocus
            disabled={saving}
            maxLength={500}
            value={text}
            onChange={(e) => updateDraft({
              text: e.target.value,
              sessionId: text ? draft.sessionId : sessionId,
              skillId: text ? draft.skillId : skillId,
              unconfirmed: Boolean(e.target.value) && draft.unconfirmed,
            })}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                void submit()
              }
            }}
            aria-label="Thought to save"
            className="min-h-16"
          />
          <p className="text-sm text-muted">{text.length}/500 characters. {storageError ? 'Draft is available here while this page stays open.' : 'Draft retained in this browser tab until saved or cleared.'}</p>
          {storageError && <p role="alert" className="text-sm">{storageError}</p>}
          {text && (draft.sessionId !== sessionId || draft.skillId !== skillId) && <p className="text-sm">This draft keeps its original session and skill context; you are now in a different learning context.</p>}
          {draft.unconfirmed && !saving && !error && <p role="alert" className="text-sm">An earlier save is unconfirmed. Check Saved thoughts before trying again; it may already be saved.</p>}
          <div className="flex flex-wrap gap-2 justify-end mt-2">
            <Dialog.Close asChild>
              <Button variant="ghost">Close</Button>
            </Dialog.Close>
            <Button variant="primary" onClick={() => void submit()} disabled={saving || !text.trim()}>
              {saving ? 'Saving…' : 'Save thought'}
            </Button>
          </div>
          {error && <p role="alert" className="mt-2 text-sm">{error}</p>}
          {saving && <p role="status" className="mt-2 text-sm">Saving your thought… Closing does not cancel the save.</p>}
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-medium">Saved thoughts</summary>
            <div className="mt-2">
              <ParkedList />
            </div>
          </details>
        </Dialog.Content>
      </Dialog.Portal>
      {status && (
        <p
          role="status"
          className="max-w-sm rounded-md bg-card border border-line px-3 py-2 text-sm"
        >
          {status}
        </p>
      )}
    </Dialog.Root>
    </div>
  )
}
