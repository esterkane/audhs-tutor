import { useQuery } from '@tanstack/react-query'
import { apiFetch, ApiError, type SkillList } from '../../lib/api'

/** Bound the read so an unresponsive local proxy cannot lock Home indefinitely. */
export async function fetchSkills(signal: AbortSignal): Promise<SkillList> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  signal.addEventListener('abort', cancel, { once: true })
  if (signal.aborted) cancel()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, 15_000)
  try {
    return await apiFetch<SkillList>('/api/skills', { signal: controller.signal })
  } catch (error) {
    if (timedOut)
      throw new ApiError(
        408,
        'lesson_check_timeout',
        'The lesson check took too long. Retry when the local app is responding.',
      )
    throw error
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', cancel)
  }
}

export function useSkills() {
  return useQuery({ queryKey: ['skills'], queryFn: ({ signal }) => fetchSkills(signal), retry: false })
}
