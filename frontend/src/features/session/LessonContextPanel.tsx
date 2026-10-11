import { useContext, useEffect, useRef, useState } from 'react'
import type { SessionOut } from '../../lib/api'
import { Button } from '../../components/ui/button'
import { LessonFocusContext } from './focusContext'
import { SessionContext } from './SessionContext'

/** Read-only responsive context. The lesson and all mutation owners stay mounted elsewhere. */
export function LessonContextPanel({ data }: { data: SessionOut }) {
  const focus = useContext(LessonFocusContext)
  const focusActive = useRef(focus?.active)
  useEffect(() => { focusActive.current = focus?.active }, [focus?.active])
  const panel = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLSpanElement>(null)
  const title = useRef<HTMLHeadingElement>(null)
  const [desktop, setDesktop] = useState(() => window.matchMedia('(min-width: 80rem)').matches)
  const [open, setOpen] = useState(false)
  const expanded = desktop && !focus?.active
  const supported = typeof HTMLElement.prototype.showPopover === 'function'
  useEffect(() => {
    const media = window.matchMedia('(min-width: 80rem)')
    let heldPreviously = false
    const trackFocus = () => { heldPreviously = !!(panel.current?.contains(document.activeElement) || trigger.current?.contains(document.activeElement)) }
    const change = () => {
      const heldFocus = panel.current?.contains(document.activeElement) || trigger.current?.contains(document.activeElement) || (document.activeElement === document.body && heldPreviously)
      if (panel.current?.matches(':popover-open')) panel.current.hidePopover()
      setOpen(false)
      setDesktop(media.matches)
      if (heldFocus) requestAnimationFrame(() => (media.matches && !focusActive.current ? title.current : trigger.current?.querySelector('button'))?.focus())
    }
    document.addEventListener('focusin', trackFocus)
    media.addEventListener('change', change)
    return () => { media.removeEventListener('change', change); document.removeEventListener('focusin', trackFocus) }
  }, [])
  function close() {
    panel.current?.hidePopover()
    trigger.current?.querySelector('button')?.focus()
  }
  return <aside className="lesson-context-column">
    {!expanded && supported && <span ref={trigger}><Button aria-expanded={open} aria-controls="lesson-context-panel"
      onClick={() => { panel.current?.togglePopover(); if (!open) title.current?.focus() }}>
      Learning context
    </Button></span>}
    <div id="lesson-context-panel" ref={panel} popover={!expanded && supported ? 'auto' : undefined}
      role="region" aria-labelledby="lesson-context-title" className="lesson-context-panel"
      onToggle={event => setOpen(event.newState === 'open')}
      onKeyDown={event => { if (!expanded && event.key === 'Escape') { event.preventDefault(); close() } }}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 ref={title} tabIndex={-1} id="lesson-context-title" className="text-panel-heading font-semibold">Learning context</h2>
        {!expanded && supported && <Button onClick={close}>Close context</Button>}
      </div>
      <SessionContext data={data} />
    </div>
  </aside>
}
