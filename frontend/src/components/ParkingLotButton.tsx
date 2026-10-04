import { useLocation } from 'react-router-dom'
import { CAPTURE_REQUEST } from '../features/parking/requestCapture'
import { validThoughtContext, type ThoughtContext } from '../features/parking/context'
import { captureThoughtContext } from '../features/parking/context'
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
  const location = useLocation()
  const [requestedContext, setRequestedContext] = useState<ThoughtContext>()
  const [captureNotice, setCaptureNotice] = useState('')
  const sourceTrigger = useRef<HTMLElement | null>(null)
  const [open, setOpen] = useState(false)
  const { draft, update: updateDraft, storageError } = useThoughtDraft()
  const text = draft.text
  const pending = useRef<AbortController | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const { invalidate } = useParkingActions()

  useEffect(() => () => { pending.current?.abort(); pending.current = null }, [])

  useEffect(() => {
    const receive = (event: Event) => {
      const detail = (event as CustomEvent).detail
      if (!validThoughtContext(detail?.context)) return
      sourceTrigger.current = detail.trigger instanceof HTMLElement ? detail.trigger : null
      setRequestedContext(detail.context)
      setCaptureNotice(text ? 'Your unfinished thought and its original material are kept. Save it first, then choose Save a thought about this passage again for a new thought.' : '')
      setOpen(true)
    }
    window.addEventListener(CAPTURE_REQUEST, receive)
    return () => window.removeEventListener(CAPTURE_REQUEST, receive)
  }, [text])

  async function submit() {
    if (!text.trim() || pending.current) return
    const controller = new AbortController()
    pending.current = controller
    let timer: ReturnType<typeof setTimeout> | undefined
    const requestKey = draft.requestKey ?? crypto.randomUUID()
    updateDraft({ ...draft, requestKey, unconfirmed: true })
    setSaving(true)
    setError('')
    setStatus(null)
    try {
      const saved = await Promise.race([
        api.park({ session_id: draft.sessionId, text: text.trim(), node_id: draft.skillId, request_key: requestKey, original_context: draft.originalContext }, controller.signal),
        new Promise<never>((_, reject) => { timer = setTimeout(() => { controller.abort(); reject(new Error('Save wait timed out')) }, 15000) }),
      ])
      if (pending.current !== controller) return
      updateDraft({ text: '', sessionId: null, skillId: null, unconfirmed: false })
      invalidate()
      setStatus(saved.status === 'dropped' ? 'This thought was already saved and later removed. Retrying did not restore it.' : saved.status === 'promoted' ? 'This thought is already saved and shown on Home.' : 'Thought saved. Open Save for later to find it under Saved thoughts.')
      setOpen(false)
    } catch {
      if (pending.current !== controller) return
      invalidate()
      setError('Could not confirm the save. Your text is still here. Retrying this unchanged thought checks the same save without creating another copy.')
    } finally {
      clearTimeout(timer)
      if (pending.current === controller) { pending.current = null; setSaving(false) }
    }
  }

  return (
    <div className="grid gap-2 min-w-0 max-w-full">
    <Dialog.Root open={open} onOpenChange={next => { setOpen(next); if (next) { setRequestedContext(undefined); setCaptureNotice(''); sourceTrigger.current = null } }}>
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
          onCloseAutoFocus={event => { if (sourceTrigger.current?.isConnected) { event.preventDefault(); sourceTrigger.current.focus() } sourceTrigger.current = null }}
          aria-describedby="park-desc"
        >
          <Dialog.Title className="text-lg font-semibold">Save a thought for later</Dialog.Title>
          <Dialog.Description id="park-desc" className="text-sm text-muted mb-2">
            Save an idea without leaving your work. Press Enter to save or Shift+Enter for a new line. Session and skill context are included when available.
          </Dialog.Description>
          {captureNotice && <p role="status" className="text-sm mb-2">{captureNotice}</p>}
          {!text && requestedContext && <p className="text-sm mb-2">Original material: {requestedContext.label}</p>}
          <Textarea
            autoFocus
            disabled={saving}
            maxLength={500}
            value={text}
            onChange={(e) => { setError(''); updateDraft({
              text: e.target.value,
              sessionId: text ? draft.sessionId : sessionId,
              skillId: text ? draft.skillId : skillId,
              unconfirmed: Boolean(e.target.value) && draft.unconfirmed,
              requestKey: e.target.value === text ? draft.requestKey : undefined,
              originalContext: text ? draft.originalContext : requestedContext ?? captureThoughtContext(location.pathname, Array.from(document.querySelectorAll('[data-capture-query]')).at(-1)?.getAttribute('data-capture-query') ?? location.search, Array.from(document.querySelectorAll('[data-capture-query]')).at(-1)?.getAttribute('data-capture-label') ?? document.querySelector('main h1')?.textContent ?? 'Original material'),
            }) }}
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
          {text && <p className="text-sm">{draft.originalContext ? `Original material: ${draft.originalContext.label}. Opening it later does not restore temporary output or playback.` : 'No exact material link is attached to this thought.'}</p>}
          {storageError && <p role="alert" className="text-sm">{storageError}</p>}
          {text && (draft.sessionId !== sessionId || draft.skillId !== skillId) && <p className="text-sm">This draft keeps its original session and skill context; you are now in a different learning context.</p>}
          {draft.unconfirmed && !saving && !error && <p role="alert" className="text-sm">{draft.requestKey ? 'An earlier save is unconfirmed. Retry this unchanged thought without creating another copy.' : 'An earlier save is unconfirmed. This older or edited draft cannot be matched to it. Check Saved thoughts first; saving now creates a new thought.'}</p>}
          <div className="flex flex-wrap gap-2 justify-end mt-2">
            <Dialog.Close asChild>
              <Button variant="ghost">Close</Button>
            </Dialog.Close>
            <Button variant="primary" onClick={() => void submit()} disabled={saving || !text.trim()}>
              {saving ? 'Saving…' : draft.unconfirmed && !draft.requestKey ? 'Save as new thought' : 'Save thought'}
            </Button>
          </div>
          {error && <p role="alert" className="mt-2 text-sm">{error}</p>}
          {saving && <p role="status" className="mt-2 text-sm">Saving your thought… Closing does not cancel the save.</p>}
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-medium">Saved thoughts</summary>
            <div className="mt-2">
              <ParkedList onOpenContext={() => setOpen(false)} />
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
