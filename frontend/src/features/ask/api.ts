import { streamReply } from '../playground/streamTutor'
import type { Schemas } from '../../lib/api'

export function askQuestion(
  body: Schemas['AskQuestion'],
  signal: AbortSignal,
  key: string,
  onToken: (text: string) => void,
) {
  return streamReply<Schemas['AskReply']>('/api/ask/stream', body, signal, key, onToken)
}
