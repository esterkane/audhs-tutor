import { streamTutor } from './streamTutor'
import { apiFetch, type Schemas } from '../../lib/api'
export type TutorRequest = Schemas['PlaygroundRequest']
export type TutorReply = Schemas['PlaygroundReply']
export function askTutor(
  body: TutorRequest,
  signal: AbortSignal,
  requestKey?: string,
  onToken?: (text: string) => void,
) {
  if (onToken && ['explain', 'hint', 'chat'].includes(body.intent ?? ''))
    return streamTutor(body, signal, requestKey, onToken)
  return apiFetch<TutorReply>('/api/playground/tutor', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
    ...(requestKey ? { headers: { 'Idempotency-Key': requestKey } } : {}),
  })
}
