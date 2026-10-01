import { apiFetch, type Schemas } from '../../lib/api'
export type TutorRequest = Schemas['PlaygroundRequest']
export type TutorReply = Schemas['PlaygroundReply']
export function askTutor(body: TutorRequest, signal: AbortSignal, requestKey?: string) {
  return apiFetch<TutorReply>('/api/playground/tutor', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
    ...(requestKey ? { headers: { 'Idempotency-Key': requestKey } } : {}),
  })
}
