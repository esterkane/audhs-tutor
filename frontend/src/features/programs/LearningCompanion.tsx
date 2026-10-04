import { useEffect, useRef, useState } from 'react'
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
export function LearningCompanion() {
  const location = useLocation()
  const [restored] = useState(restore)
  const [context, setContext] = useState(restored.context)
  const [storageError, setStorageError] = useState(restored.error)
  const [open, setOpen] = useState(false)
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
  function capture(): Capture {
    const selection = window.getSelection()?.toString().trim() ?? ''
    return {
      id: crypto.randomUUID(),
      text: (selection || document.querySelector('main')?.innerText.trim() || '').slice(0, 12000),
      title: (document.querySelector('main h1')?.textContent || 'Captured page').slice(0, 200),
      path: (location.pathname + location.search).slice(0, 2000),
    }
  }
  return (
    <section aria-label="Learning companion" className="border-t border-line p-4 max-w-3xl mx-auto">
      <Button variant="outline" asChild><button type="button" ref={launcher} onClick={() => {
        if (!active) { const next = capture(); setContext({ active: next, draft: next, previous: null }) }
        setOpen(true)
      }}>{active ? 'Reopen learning companion' : 'Listen or ask about this page'}</button></Button>
      {active && !open && <p className="text-sm mt-2">Reopen your discussion of {active.title}. New page material is added only when you choose it.</p>}
      {storageError && <p role="alert" className="text-sm mt-2">{storageError}</p>}
      {open && active && draft && <div className="grid gap-3 mt-3">
        <p>Discussing material captured from <Link className="underline" to={active.path}>{active.title}</Link>.</p>
        {active.path !== location.pathname + location.search && <p role="status">You are browsing another page. The tutor still uses the captured material above.</p>}
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
        <Button variant="ghost" onClick={() => { setOpen(false); launcher.current?.focus() }}>Close learning companion</Button>
      </div>}
    </section>
  )
}
