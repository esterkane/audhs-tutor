import { createPortal } from 'react-dom'
import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { ReadAloud } from '../voice/ReadAloud'
import { StudyTutor } from './StudyTutor'

type Capture = { id: string; text: string; title: string; path: string }
type Context = { active: Capture | null; draft: Capture | null; previous: Capture | null }
const KEY = 'learning-companion:context:v1'
const empty: Context = { active: null, draft: null, previous: null }
function valid(value: unknown): value is Capture | null {
  if (value === null) return true
  if (!value || typeof value !== 'object') return false
  const c = value as Capture
  return typeof c.id === 'string' && /^[a-f0-9-]{36}$/.test(c.id) && typeof c.text === 'string' && c.text.length <= 12000 &&
    typeof c.title === 'string' && c.title.length <= 200 &&
    typeof c.path === 'string' && c.path.length <= 2000 && /^\/(?!\/)/.test(c.path) && !Array.from(c.path).some(char => char === '\\' || char.charCodeAt(0) < 32)
}
function restore(): { context: Context; error: string } {
  try {
    const raw = sessionStorage.getItem(KEY)
    if (!raw) return { context: empty, error: '' }
    if (raw.length > 100000) throw new Error('Oversized checkpoint')
    const saved = JSON.parse(raw)
    if (saved.version !== 1 || !valid(saved.active) || !valid(saved.draft) || !valid(saved.previous)) throw new Error('Invalid checkpoint')
    return { context: { active: saved.active, draft: saved.draft, previous: saved.previous }, error: '' }
  } catch {
    return { context: empty, error: 'Captured material could not be restored in this tab. Capture the page again.' }
  }
}

/** Browsing never silently changes the applied material or conversation target. */
export function LearningCompanion({ entryRoot }: { entryRoot: HTMLElement | null }) {
  const location = useLocation()
  const [restored] = useState(restore)
  const [context, setContext] = useState(restored.context)
  const [storageError, setStorageError] = useState(restored.error)
  const [open, setOpen] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const { active, draft, previous } = context
  const changed = JSON.stringify(draft) !== JSON.stringify(active)
  useEffect(() => {
    if (context === restored.context && restored.error) return
    try {
      sessionStorage.setItem(KEY, JSON.stringify({ version: 1, ...context }))
      // eslint-disable-next-line react-hooks/set-state-in-effect
      if (storageError) setStorageError('')
    }
    catch {
      // External storage failure must not discard the active in-memory context.
      setStorageError('Captured material could not be saved in this tab. Copy it before reloading.')
    }
  }, [context, restored, storageError])
  useLayoutEffect(() => {
    const node = dialog.current
    if (!node) return
    if (!open) { node.close(); return }
    const desktop = window.matchMedia('(min-width: 64rem)')
    function present() {
      if (!node) return
      const focused = document.activeElement
      const retainedFocus = focused instanceof HTMLElement && node.contains(focused) ? focused : null
      if (node.open) node.close()
      if (desktop.matches) node.show()
      else node.showModal()
      if (retainedFocus) retainedFocus.focus()
      else closeButton.current?.focus()
    }
    present()
    desktop.addEventListener('change', present)
    return () => desktop.removeEventListener('change', present)
  }, [open])
  function close() {
    dialog.current?.close()
    setOpen(false)
    launcher.current?.focus()
  }
  function capture(): Capture {
    const selection = window.getSelection()?.toString().trim() ?? ''
    return {
      id: crypto.randomUUID(),
      text: (selection || document.querySelector('main')?.innerText.trim() || '').slice(0, 12000),
      title: (document.querySelector('main h1')?.textContent || 'Captured page').slice(0, 200),
      path: (location.pathname + location.search).slice(0, 2000),
    }
  }
  const entry = <>
      <Button variant="outline" asChild><button type="button" ref={launcher} aria-expanded={open} aria-controls="learning-companion" onClick={() => {
        if (!active) { const next = capture(); setContext({ active: next, draft: next, previous: null }) }
        setOpen(true)
      }}>{active ? 'Reopen learning companion' : 'Listen or ask about this page'}</button></Button>

      {storageError && <p role="alert" className="text-sm mt-2">{storageError}</p>}
  </>
  return <>
    {entryRoot && createPortal(entry, entryRoot)}
    <dialog ref={dialog} id="learning-companion" aria-label="Learning companion" className="companion" data-open={open}
      onCancel={event => { event.preventDefault(); close() }}>
      {open && active && draft && <>
      <div className="companion-heading">
        <h2 className="font-semibold">Tutor</h2>
        <Button variant="ghost" asChild><button ref={closeButton} onClick={close}>Close learning companion</button></Button>
      </div>
      <div className="grid gap-3 p-4">
        <p>Discussing material captured from <Link className="underline" to={active.path} onClick={() => {
          if (dialog.current?.matches(':modal')) { close(); document.querySelector<HTMLElement>('main')?.focus() }
        }}>{active.title}</Link>.</p>
        {active.path !== location.pathname + location.search && <p role="status">You are browsing another page. The tutor still uses the captured material above.</p>}
        <p className="text-sm companion-selection-help">On narrow screens, close the tutor to select page text, then reopen and capture it.</p>
        <p className="text-sm">Select page text for focused help. Only the captured text (up to 12,000 characters) is used. Editing below does not change the tutor’s material until you apply it.</p>
        <Button onClick={() => setContext(old => ({ ...old, draft: capture() }))}>Capture current page for review</Button>
        <label>Material to discuss
          <textarea className="block w-full bg-card border border-control rounded p-2" maxLength={12000} value={draft.text}
            onChange={event => setContext(old => ({ ...old, draft: { ...draft, text: event.target.value } }))} />
        </label>
        {changed && <div className="grid gap-2">
          <p role="status">Unapplied material from {draft.title}. Apply starts a separate discussion. Only one previous capture is kept here.</p>
          <Button disabled={!draft.text.trim()} onClick={() => { const next = { ...draft, id: crypto.randomUUID() }; setContext({ active: next, draft: next, previous: active }) }}>Apply material</Button>
          <Button onClick={() => setContext(old => ({ ...old, draft: active }))}>Discard material edits</Button>
        </div>}
        {previous && <Button disabled={changed} onClick={() => setContext({ active: previous, draft: previous, previous: active })}>Return to previous material</Button>}
        <ReadAloud key={`read:${active.id}`} text={active.text} />
        <StudyTutor key={`tutor:${active.id}`} identity={`companion:${active.id}`} context={active.text} targetLabel={active.title} />
        <p className="text-sm text-muted">Closing stops local audio, microphone and waiting for a reply. A pending request can be recovered when you reopen; closing does not guarantee cancellation on the server.</p>
      </div></>}
    </dialog>
  </>
}
