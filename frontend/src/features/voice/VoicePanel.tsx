import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Textarea } from '../../components/ui/textarea'
import { Markdown } from '../../components/Markdown'
import { useVoiceLoop } from './useVoiceLoop'

/**
 * Talk to the tutor (P9). Connect → Talk (mic opens) → the transcript appears → the answer streams
 * as text and, when a voice is ready, as audio. Interrupt stops playback at once. Typing stays
 * available in the same conversation (text-only fallback), and the transcript is always shown.
 * In conversation mode (language block) the reply follows the conversation prompt in `lang`.
 */
export function VoicePanel({
  sessionId,
  skillId,
  lang,
  conversation = false,
  title = 'Talk to the tutor',
  makeSocket,
  onClose,
}: {
  sessionId: string
  skillId?: string | null
  lang?: string | null
  conversation?: boolean
  title?: string
  makeSocket?: (url: string) => WebSocket
  onClose?: () => void
}) {
  const v = useVoiceLoop({ sessionId, skillId, lang, conversation, makeSocket })
  const [typed, setTyped] = useState('')
  const textOnly = v.ready?.text_only === true
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      {v.status === 'idle' && (
        <div className="mt-2">
          <p className="text-sm text-muted mb-2">
            Nothing is recorded until you press Talk; the microphone closes when you press Done. The
            transcript and the answer stay readable as text.
          </p>
          <Button variant="primary" onClick={v.connect}>
            Connect
          </Button>
        </div>
      )}
      {v.status !== 'idle' && (
        <>
          {/* announced only when it matters: ready/text-only, speaking (an action is available), error */}
          <p className="text-xs text-muted mt-1" role="status">
            {v.status === 'ready' && (textOnly ? `Text only (${String(v.ready?.why_text_only)})` : 'Ready')}
            {v.status === 'speaking' && 'Speaking — press Interrupt to stop'}
            {v.status === 'error' && 'Voice unavailable — typing still works'}
          </p>
          <p className="text-xs text-muted" aria-live="off">
            {v.status === 'connecting' && 'Connecting…'}
            {v.status === 'listening' && 'Listening…'}
            {v.status === 'thinking' && 'Thinking…'}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {!textOnly && v.status !== 'listening' && (
              <Button variant="primary" onClick={() => void v.listen()} disabled={v.status === 'connecting'}>
                Talk
              </Button>
            )}
            {v.status === 'listening' && (
              <Button variant="primary" onClick={v.stopListening}>
                Done
              </Button>
            )}
            {(v.status === 'speaking' || v.status === 'thinking') && (
              <Button variant="secondary" onClick={v.interrupt}>
                Interrupt
              </Button>
            )}
            <Button
              variant="ghost"
              onClick={() => {
                v.close()
                onClose?.()
              }}
            >
              Stop voice
            </Button>
          </div>
          {v.nothingHeard && (
            <p className="text-sm text-muted mt-2" role="status">
              Nothing heard. Try again closer to the microphone, or type below.
            </p>
          )}
          {v.error && (
            <p className="text-sm text-warn mt-2" role="alert">
              {v.error}
            </p>
          )}
          {v.transcript && (
            <p className="text-sm mt-3">
              <span className="text-muted">You said:</span> {v.transcript}
            </p>
          )}
          {v.answer && (
            <div className="mt-2">
              <Markdown text={v.answer} />
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2 items-end">
            <label className="text-sm flex-1 min-w-48">
              Type instead
              <Textarea value={typed} onChange={(e) => setTyped(e.target.value)} className="mt-1 min-h-10" />
            </label>
            <Button
              variant="secondary"
              disabled={!typed.trim() || v.status === 'connecting'}
              onClick={() => {
                v.sendText(typed)
                setTyped('')
              }}
            >
              Send
            </Button>
          </div>
        </>
      )}
    </Card>
  )
}
