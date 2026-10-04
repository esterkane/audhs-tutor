import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { apiFetch, type SessionOut } from '../../lib/api'
import { useMode } from '../../stores/mode'
import { routeForPhase } from '../session/api'
import type { ThoughtContext } from './context'

/** A historical lesson identity is not permission to replace today's active session. */
export function OriginalLesson({ context, onOpen }: { context: Extract<ThoughtContext, { kind: 'lesson' }>; onOpen?: () => void }) {
  const nav = useNavigate()
  const { setSession } = useMode()
  const pending = useRef<AbortController | null>(null)
  const [checking, setChecking] = useState(false)
  const [message, setMessage] = useState('')
  const [moved, setMoved] = useState(false)
  useEffect(() => () => { pending.current?.abort(); pending.current = null }, [])
  async function open() {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setChecking(true); setMessage(''); setMoved(false)
    const deadline = setTimeout(() => controller.abort(), 15000)
    try {
      const current = await apiFetch<SessionOut | null>('/api/sessions/current', { signal: controller.signal })
      if (pending.current !== controller || controller.signal.aborted) return
      const st = current?.state
      if (current?.id === context.session_id && st?.skill_id === context.skill_id && st.block_index === context.block_index && st.block_started_at === context.block_started_at && st.block_status === 'running' && !st.plan_complete) {
        setSession(current.id, context.skill_id)
        onOpen?.()
        nav(routeForPhase(st))
      } else {
        setMoved(true)
        setMessage('Your learning session has moved on. Open the original lesson choices to keep your current session or explicitly start this lesson again.')
      }
    } catch {
      if (pending.current === controller) setMessage('Could not check your current session. Nothing was changed. Try opening the original lesson again.')
    } finally {
      clearTimeout(deadline)
      if (pending.current === controller) { pending.current = null; setChecking(false) }
    }
  }
  return <div className="w-full grid gap-2">
    <Button disabled={checking} onClick={() => void open()}>{checking ? 'Checking saved lesson…' : `Open original lesson: ${context.label}`}</Button>
    {message && <p role="status">{message}</p>}
    {moved && <Link className="underline" to={`/?lesson=${encodeURIComponent(context.skill_id)}`} onClick={onOpen}>Choose whether to return to this lesson</Link>}
  </div>
}
