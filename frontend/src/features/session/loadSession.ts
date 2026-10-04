import type { SessionOut } from '../../lib/api'
import { boundedRead, READ_TIMEOUT_MS } from '../../lib/boundedRead'

export const SESSION_LOAD_TIMEOUT_MS = READ_TIMEOUT_MS
export function loadSession(id: string, signal: AbortSignal): Promise<SessionOut> {
  return boundedRead<SessionOut>(`/api/sessions/${encodeURIComponent(id)}`, signal, 'Session')
}
