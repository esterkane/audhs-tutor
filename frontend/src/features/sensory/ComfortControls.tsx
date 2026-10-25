import { useEffect, useRef, useState } from 'react'
import { useComfort } from './comfortStore'
import { useLocation, Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { usePreferences } from '../preferences/api'
import { useGenerationActivity } from './generationActivity'

export function ComfortToggle() {
  const { focus, setFocus } = useComfort()
  return <Button variant="secondary" className="px-2 md:px-4" aria-label={focus ? 'Exit focus mode' : 'Focus mode'} title={focus ? 'Exit focus mode' : 'Focus mode'} aria-pressed={focus} onClick={() => setFocus(!focus)}>
    <span aria-hidden="true">⛶</span><span className="hidden md:inline">{focus ? 'Exit focus mode' : 'Focus mode'}</span>
  </Button>
}

export function BreakReminder() {
  const { pathname } = useLocation()
  const prefs = usePreferences()
  const minutes = Number(prefs.data?.values?.['ui.break_reminder'] ?? 25)
  const generating = useGenerationActivity(s => s.count > 0)
  const [due, setDue] = useState(false)
  const [intervalMinutes, setIntervalMinutes] = useState(minutes)
  if (intervalMinutes !== minutes) { setIntervalMinutes(minutes); setDue(false) }
  const [editing, setEditing] = useState(false)
  const elapsed = useRef(0)
  const lastActivity = useRef(0)
  const previousTick = useRef(0)
  useEffect(() => { elapsed.current = 0 }, [minutes])
  const learning = /^\/(session|ask|curriculum|programs|playground|review|practice|learn)(\/|$)/.test(pathname)
  useEffect(() => {
    function activity() { lastActivity.current = Date.now() }
    function focus() {
      const el = document.activeElement
      setEditing(el instanceof Element && !!el.closest('textarea, input:not([type=button]):not([type=submit]), [contenteditable=true], .cm-editor'))
    }
    activity()
    previousTick.current = Date.now()
    window.addEventListener('pointerdown', activity)
    window.addEventListener('keydown', activity)
    document.addEventListener('focusin', focus)
    const blur = () => queueMicrotask(focus)
    document.addEventListener('focusout', blur)
    const timer = setInterval(() => {
      const now = Date.now()
      const delta = Math.min(1000, Math.max(0, now - previousTick.current))
      previousTick.current = now
      if (!learning || minutes === 0 || document.hidden || now - lastActivity.current > 60_000) return
      elapsed.current += delta
      if (elapsed.current >= minutes * 60_000) setDue(true)
    }, 1000)
    return () => {
      clearInterval(timer)
      window.removeEventListener('pointerdown', activity)
      window.removeEventListener('keydown', activity)
      document.removeEventListener('focusin', focus)
      document.removeEventListener('focusout', blur)
    }
  }, [learning, minutes])
  function dismiss() { elapsed.current = 0; setDue(false) }
  if (!learning || minutes === 0 || !due || generating || editing) return null
  return <aside aria-label="Gentle break reminder" className="rounded border border-line bg-card p-3 mb-4">
    <p role="status">You’ve been learning for a while. A short break is available whenever you’re ready.</p>
    <div className="flex flex-wrap gap-2 mt-2">
      <Button variant="secondary" onClick={dismiss}>Keep learning</Button>
      <Link to="/together" onClick={dismiss} className="underline">Open the quiet break space</Link>
    </div>
    <p className="text-sm text-muted">Your session stays open. Change or turn off reminders in Preferences.</p>
  </aside>
}

/** An optional first-visit hint, never a gate before learning. */
export function ComfortWelcome() {
  const [show, setShow] = useState(() => {
    try { return localStorage.getItem('audhs-comfort-welcome') !== 'seen' }
    catch { return false }
  })
  function dismiss() {
    setShow(false)
    try { localStorage.setItem('audhs-comfort-welcome', 'seen') } catch { /* Reading stays available. */ }
  }
  if (!show) return null
  return <aside aria-label="Reading comfort" className="rounded border border-line p-3 mb-4">
    <p>Make this space comfortable: adjust motion and text size in Preferences. Decorative effects are off.</p>
    <div className="flex flex-wrap gap-3 items-center"><Link to="/preferences" onClick={dismiss} className="underline">Adjust reading comfort</Link><Button variant="ghost" onClick={dismiss}>Skip comfort setup</Button></div>
  </aside>
}
