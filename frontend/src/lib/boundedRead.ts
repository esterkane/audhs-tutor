import { apiFetch } from './api'

export const READ_TIMEOUT_MS = 15000

/** Bound the whole response, even when a transport ignores AbortSignal. */
export async function boundedRead<T>(path: string, signal: AbortSignal, label: string, init?: Omit<RequestInit, 'signal'>): Promise<T> {
  const controller = new AbortController()
  let timer: ReturnType<typeof setTimeout> | undefined
  let cancel: () => void = () => {}
  const deadline = new Promise<never>((_, reject) => {
    cancel = () => {
      controller.abort()
      reject(new Error(`${label} loading was cancelled.`))
    }
    signal.addEventListener('abort', cancel, { once: true })
    if (signal.aborted) cancel()
    timer = setTimeout(() => {
      controller.abort()
      reject(new Error(`${label} loading took too long. Check the local backend and retry.`))
    }, READ_TIMEOUT_MS)
  })
  try {
    return await Promise.race([apiFetch<T>(path, { ...init, signal: controller.signal }), deadline])
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', cancel)
  }
}
