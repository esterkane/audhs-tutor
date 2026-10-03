import { AnswerSaveStatus } from '../programs/AnswerSaveStatus'
import { AudioControls } from '../audio/AudioControls'
import { useEffect, useState } from 'react'
import { useVoiceRequestRecovery } from './useVoiceRequestRecovery'
import { useVoiceTextRecovery } from './useVoiceTextRecovery'
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
function ScopedVoicePanel({
  sessionId,
  skillId,
  lang,
  conversation = false,
  title = 'Talk to the tutor',
  makeSocket,
  onClose,
  onReset,
}: {
  sessionId: string
  skillId?: string | null
  lang?: string | null
  conversation?: boolean
  title?: string
  makeSocket?: (url: string) => WebSocket
  onClose?: () => void
  onReset: () => void
}) {
  const scope = JSON.stringify([sessionId, skillId ?? null, lang ?? null, conversation])
  const recovery = useVoiceTextRecovery(scope)
  const request = useVoiceRequestRecovery(scope, sessionId)
  const v = useVoiceLoop({
    sessionId,
    skillId,
    lang,
    conversation,
    makeSocket,
    initialText: recovery.initial,
    onRequest: request.begin,
    onTerminal: request.finish,
  })
  const [typed, setTyped] = useState(recovery.initial.draft)
  const { save } = recovery
  useEffect(() => {
    save({ draft: typed, transcript: v.transcript, answer: v.answer, interrupted: v.interrupted })
  }, [save, typed, v.transcript, v.answer, v.interrupted])
  const textOnly = v.ready?.text_only === true
  return (
    <Card>
      <CardTitle>{title}</CardTitle>
      <AudioControls />
      {v.audioNotice && <p role="status">{v.audioNotice}</p>}
      {recovery.restored && (
        <p role="status" className="text-sm mt-2">
          Restored voice text from this tab; it may be incomplete. No connection, recording or playback has
          restarted. Check saved answers for completed replies.
        </p>
      )}
      {recovery.error && (
        <p role="alert" className="text-sm mt-2">
          {recovery.error}
        </p>
      )}
      {request.error && <p role="alert" className="text-sm mt-2">{request.error}</p>}
      {request.error && !request.memoryOnly && (
        <Button onClick={request.useMemoryOnly}>Continue for this page only</Button>
      )}
      {request.memoryOnly && <p role="status">Request recovery is in memory only; reloading may lose it. Previously saved tab data may still exist.</p>}
      {request.pending && (v.status === 'idle' || v.status === 'error' || v.status === 'ready') && (
        <section aria-label="Recover voice reply" className="mt-3 space-y-2">
          <p>A previous voice request may have a saved reply. Check it before starting another question.</p>
          <Button disabled={request.checking} onClick={() => { v.close(); void request.check().then((result) => { if (result) v.restoreResult(result) }) }}>
            {request.checking ? 'Checking saved result…' : 'Check saved voice result'}
          </Button>
          <Button variant="ghost" onClick={() => { v.close(); request.discard() }}>
            Dismiss recovery and allow a new question
          </Button>
          <p className="text-sm">Dismissing does not cancel server work or delete a saved answer. Sending again creates a new request.</p>
          {request.result && (
            <div role="status">
              {request.result.status === 'not_found' && <p>No recorded result yet. Recording or transcription may have stopped before a response was registered. Check again later; nothing was resent.</p>}
              {request.result.status === 'unresolved' && <p>The request was registered, but no final result is available. It may still be finishing or may have stopped. Checking again will not regenerate it.</p>}
              {request.result.status === 'partial' && <p>Recovered partial reply. It may be incomplete; no audio was played.</p>}
              {request.result.status === 'completed' && <p>Recovered completed reply. No new answer was generated and no audio was played.</p>}

            </div>
          )}
        </section>
      )}
      {(v.status === 'idle' || v.status === 'error') && (
        <div className="mt-2">
          <p className="text-sm text-muted mb-2">
            Nothing is recorded until you press Talk; the microphone closes when you press Done. The
            transcript and the answer stay readable as text.
          </p>
          <Button
            variant="primary"
            onClick={() => {
              if (v.status === 'error') v.close()
              v.connect()
            }}
          >
            {v.status === 'error' ? 'Reconnect' : 'Connect'}
          </Button>
        </div>
      )}
      {v.status !== 'idle' && (
        <>
          {/* announced only when it matters: ready/text-only, speaking (an action is available), error */}
          <p className="text-xs text-muted mt-1" role="status">
            {v.status === 'ready' && (textOnly ? `Text only (${String(v.ready?.why_text_only)})` : 'Ready')}
            {v.status === 'speaking' && 'Speaking — press Interrupt to stop'}
            {v.status === 'error' && 'Disconnected — your draft is kept; reconnect to send'}
          </p>
          <p className="text-xs text-muted" aria-live="off">
            {v.status === 'connecting' && 'Connecting…'}
            {v.status === 'listening' && 'Listening…'}
            {v.status === 'thinking' && 'Thinking…'}
            {v.status === 'stopping' && 'Stopping the previous turn… Received text is kept.'}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            {!textOnly && v.status !== 'listening' && (
              <Button variant="primary" onClick={() => void v.listen()} disabled={!v.canSend || !!request.pending}>
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
        </>
      )}
      {v.transcript && (
        <p className="text-sm mt-3">
          <span className="text-muted">You said:</span> {v.transcript}
        </p>
      )}
      {v.interrupted && (
        <p role="status" className="text-sm mt-2">
          Response stopped. The text below may be incomplete.
          {v.saveTurn &&
            ' Saved-answer status refers to the completed response, which may contain more text.'}
        </p>
      )}
      {v.answer && (
        <div className="mt-2">
          <Markdown text={v.answer} />
        </div>
      )}
      {v.saveTurn && (
        <AnswerSaveStatus
          key={v.saveTurn.turn_id}
          answerId={v.saveTurn.answer_id}
          receipt={v.saveTurn.save_receipt}
          error={v.saveTurn.save_error}
          text={v.saveTurn.text}
        />
      )}
      {!v.saveTurn && v.saveNote && (
        <p role="status" className="text-sm mt-2">
          {v.saveNote}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2 items-end">
        <label className="text-sm flex-1 min-w-48">
          Type instead
          <Textarea value={typed} onChange={(e) => setTyped(e.target.value)} className="mt-1 min-h-10" />
        </label>
        <Button
          variant="secondary"
          disabled={!typed.trim() || !v.canSend || !!request.pending}
          onClick={() => {
            if (v.sendText(typed)) setTyped('')
          }}
        >
          Send
        </Button>
      </div>
      {
        <Button
          variant="ghost"
          onClick={() => {
            v.close()
            if (request.discard() && recovery.clear()) {
              if (onClose) onClose()
              else onReset()
            }
          }}
        >
          {onClose ? 'Clear and close panel' : 'Clear voice text'}
        </Button>
      }
    </Card>
  )
}

/** Context changes dispose the old socket before another learning target gets its text. */
export function VoicePanel(props: Omit<Parameters<typeof ScopedVoicePanel>[0], 'onReset'>) {
  const [generation, setGeneration] = useState(0)
  const scope = JSON.stringify([
    props.sessionId,
    props.skillId ?? null,
    props.lang ?? null,
    props.conversation ?? false,
  ])
  return (
    <ScopedVoicePanel
      key={`${scope}:${generation}`}
      {...props}
      onReset={() => setGeneration((value) => value + 1)}
    />
  )
}
