import { useState } from 'react'
import { Together } from '../../routes/Together'

const KEY = 'session:alongside:v1'
function restore(sessionId: string) {
  try {
    const saved = JSON.parse(sessionStorage.getItem(KEY) ?? 'null')
    return { open: saved?.version === 1 && saved.sessionId === sessionId && saved.open === true, available: true }
  } catch {
    return { open: false, available: false }
  }
}

/** Only presentation is recovered. Audio and the presence timer remain owned by Together. */
export function AlongsideMode({ sessionId }: { sessionId: string }) {
  return <SessionAlongside key={sessionId} sessionId={sessionId} />
}

function SessionAlongside({ sessionId }: { sessionId: string }) {
  const [state, setState] = useState(() => restore(sessionId))
  return <div>
    <details open={state.open} onToggle={event => {
      const open = event.currentTarget.open
      if (open === state.open) return
      let available = true
      try {
        sessionStorage.setItem(KEY, JSON.stringify({ version: 1, sessionId, open }))
      } catch { available = false }
      setState({ open, available })
    }}>
      <summary className="cursor-pointer text-sm font-medium">Work alongside</summary>
      <p className="text-sm text-muted my-2">Keep this lesson open with a quiet work panel. Closing it keeps your answer here. This tab remembers the panel for this session; sound stays off when you return. The panel’s timer restarts when reopened.</p>
      {state.open && <Together embedded />}
    </details>
    {!state.available && <p role="status" className="text-sm text-muted">The panel works here, but this tab cannot remember it after you leave.</p>}
  </div>
}
