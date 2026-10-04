import { apiFetch, type SessionOut } from '../../lib/api'

export const SESSION_LOAD_TIMEOUT_MS = 15000

/** Bound the whole response, even when a transport ignores AbortSignal. */
export async function loadSession(id: string, signal: AbortSignal): Promise<SessionOut> {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  let cancel: () => void = () => {}
  const deadline = new Promise<never>((_, reject) => {
    cancel = () => {
      controller.abort()
      reject(new Error('Session loading was cancelled.'))
    }
    signal.addEventListener('abort', cancel, { once: true })
    if (signal.aborted) cancel()
    timer = setTimeout(() => {
      controller.abort()
      reject(new Error('Session loading took too long. Check the local backend and retry.'))
    }, SESSION_LOAD_TIMEOUT_MS)
  })
  try {
    return await Promise.race([
      apiFetch<SessionOut>(`/api/sessions/${encodeURIComponent(id)}`, { signal: controller.signal }),
      deadline,
    ])
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', cancel)
  }
}
