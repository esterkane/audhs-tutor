import { useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { useModelActions } from '../models/api'
import { startMic, wavFromPcm16, type Mic } from './audio'
import { useVoiceActions, useVoiceReadiness, type ReadinessOut } from './api'

type Comp = ReadinessOut['stt']

function Line({ name, c }: { name: string; c: Comp }) {
  return (
    <li>
      <span className="font-medium">{name}:</span> {c.status} — {c.detail}
      {!c.ready || c.status === 'fallback' ? (
        <span className="block text-muted">Next step: {c.action}</span>
      ) : null}
    </li>
  )
}

/**
 * Voice setup (P9): readiness → install (registry pulls, explicit) → verify (runtime really loads)
 * → test your microphone (recording discarded) → activate. Each step is its own button; nothing
 * downloads, starts or switches by itself. Installed ≠ activated.
 */
export function VoiceSetup() {
  const readiness = useVoiceReadiness()
  const { verify, testMic, activate } = useVoiceActions()
  const { pull } = useModelActions()
  const [recording, setRecording] = useState(false)
  const [micError, setMicError] = useState<string | null>(null)
  const mic = useRef<Mic | null>(null)
  const frames = useRef<Int16Array[]>([])
  const r = readiness.data
  if (readiness.isLoading) return <Card>Checking voice components…</Card>
  if (!r || !r.stt) return null

  async function startTest() {
    setMicError(null)
    frames.current = []
    try {
      mic.current = await startMic((pcm) => frames.current.push(pcm))
      setRecording(true)
    } catch (e) {
      setMicError((e as Error).message)
    }
  }
  function stopTest() {
    mic.current?.stop()
    mic.current = null
    setRecording(false)
    testMic.mutate(wavFromPcm16(frames.current))
    frames.current = []
  }

  return (
    <Card>
      <CardTitle>Voice</CardTitle>
      <p className="text-sm text-muted mb-2">
        Talk to the tutor and hear the answer. Speech recognition runs on this Mac (MLX Whisper); the voice
        comes from a Kokoro server you start yourself. Four separate steps, all yours to click: install,
        verify, test, activate. Recordings are deleted after transcription unless you turn retention on.
      </p>
      <ul className="text-sm grid gap-1" aria-label="Voice components">
        <Line name="Speech recognition" c={r.stt} />
        <Line name="Voice (TTS)" c={r.tts} />
        <Line name="Speech detection" c={r.vad} />
      </ul>
      <ol className="text-xs text-muted mt-2 flex flex-wrap gap-3" aria-label="Setup steps">
        <li>{r.stt.ready ? '✓ 1 installed' : '1 install'}</li>
        <li>{verify.data && verify.data.problems.length === 0 ? '✓ 2 verified' : '2 verify'}</li>
        <li>{testMic.data ? '✓ 3 mic tested' : '3 test mic'}</li>
        <li>{r.activated ? '✓ 4 activated' : '4 activate'}</li>
      </ol>
      <div className="flex flex-wrap gap-2 mt-2">
        {!r.stt.ready && r.stt.status === 'available' && (
          <Button size="sm" variant="primary" disabled={pull.isPending} onClick={() => pull.mutate(r.stt_id)}>
            1 · Download speech recognition (1.6 GB)
          </Button>
        )}
        {r.vad.status === 'fallback' && (
          <Button
            size="sm"
            variant="ghost"
            disabled={pull.isPending}
            onClick={() => pull.mutate('silero-vad')}
          >
            Optional · Download Silero VAD (2 MB)
          </Button>
        )}
        <Button
          size="sm"
          variant={r.stt.ready && r.tts.ready && !verify.data ? 'primary' : 'secondary'}
          disabled={verify.isPending}
          onClick={() => verify.mutate()}
        >
          2 · Verify the components load
        </Button>
        {!recording ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={!r.stt.ready || testMic.isPending}
            onClick={() => void startTest()}
          >
            3 · Test my microphone (record)
          </Button>
        ) : (
          <Button size="sm" variant="primary" onClick={stopTest}>
            Stop recording and transcribe
          </Button>
        )}
        <Button
          size="sm"
          variant={r.activated ? 'ghost' : 'primary'}
          disabled={activate.isPending || (!r.activated && !r.can_activate)}
          onClick={() => activate.mutate(!r.activated)}
        >
          {r.activated ? 'Deactivate voice' : '4 · Activate voice'}
        </Button>
      </div>
      {pull.isSuccess && (
        <p className="text-sm text-muted mt-2" role="status">
          Download started under Models › jobs. Come back here when it is done.
        </p>
      )}
      {verify.data && (
        <p className="text-sm mt-2" role="status">
          {verify.data.problems.length === 0
            ? `Both components answered${verify.data.tts ? ` (first audio after ${verify.data.tts.first_audio_ms} ms)` : ''}.`
            : verify.data.problems.join(' · ')}
        </p>
      )}
      {micError && (
        <p className="text-sm text-warn mt-2" role="alert">
          {micError}
        </p>
      )}
      {testMic.data && (
        <p className="text-sm mt-2" role="status">
          Heard: “{testMic.data.text || '(nothing)'}” in {testMic.data.latency_ms} ms. The recording was not
          kept.
        </p>
      )}
      {(testMic.isError || activate.isError || verify.isError) && (
        <p className="text-sm text-warn mt-2" role="alert">
          {((testMic.error ?? activate.error ?? verify.error) as Error).message}
        </p>
      )}
      <p className="text-xs text-muted mt-2">
        {r.activated
          ? 'Activated: the session screen shows a Talk button.'
          : 'Not activated: sessions stay text-only.'}{' '}
        Retention:{' '}
        {r.retain_audio
          ? `recordings kept ${r.retention_days} days`
          : 'recordings deleted after transcription'}{' '}
        (Preferences › Voice).
      </p>
    </Card>
  )
}
