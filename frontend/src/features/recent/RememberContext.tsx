import { useEffect } from 'react'
import type { ThoughtContext } from '../parking/context'
import { useRecentContexts } from './history'

/** Mount only for a successfully resolved, displayed destination. */
export function RememberContext({ context }: { context: ThoughtContext }) {
  const serialized = JSON.stringify(context)
  useEffect(() => { useRecentContexts.getState().remember(JSON.parse(serialized)) }, [serialized])
  return null
}
