import { useCallback, useState } from 'react'
import { parsePreset } from './engine'

// History retains valid graph snapshots only. Incomplete JSON remains editable but is not replayed.
export function useDraftHistory(initial: string) {
  const [state, setState] = useState({ text: initial, past: [] as string[], future: [] as string[] })
  const change = useCallback(
    (text: string) =>
      setState((s) => {
        if (s.text === text) return s
        let past = s.past
        try {
          parsePreset(s.text)
          if (past.at(-1) !== s.text) past = [...past.slice(-49), s.text]
        } catch {
          /* retain last valid checkpoint while typing */
        }
        return { text, past, future: [] }
      }),
    [],
  )
  const undo = () =>
    setState((s) => {
      const text = s.past.at(-1)
      if (!text) return s
      parsePreset(text)
      let future = s.future
      try {
        parsePreset(s.text)
        future = [s.text, ...future].slice(0, 50)
      } catch {
        /* discard invalid draft */
      }
      return { text, past: s.past.slice(0, -1), future }
    })
  const redo = () =>
    setState((s) => {
      const text = s.future[0]
      if (!text) return s
      parsePreset(text)
      return { text, past: [...s.past.slice(-49), s.text], future: s.future.slice(1) }
    })
  return {
    text: state.text,
    change,
    undo,
    redo,
    canUndo: !!state.past.length,
    canRedo: !!state.future.length,
  }
}
