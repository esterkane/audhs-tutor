import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { startMic, wavFromPcm16, type Mic } from './audio'
import { apiFetch, type Schemas } from '../../lib/api'

export function DictationButton({
  onTranscript,
  disabled = false,
}: {
  onTranscript: (text: string) => void
  disabled?: boolean
}) {
  const [state, setState] = useState<'idle' | 'opening' | 'recording' | 'transcribing'>('idle')
  const [error, setError] = useState('')
  const mic = useRef<Mic | null>(null)
  const frames = useRef<Int16Array[]>([])
  const request = useRef<AbortController | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generation = useRef(0)
  function cleanup() {
    generation.current++
    mic.current?.stop()
    mic.current = null
    request.current?.abort()
    request.current = null
    if (timer.current) clearTimeout(timer.current)
    frames.current = []
  }
  useEffect(() => () => cleanup(), [])
  function cancel() {
    cleanup()
    setState('idle')
  }
  async function finish() {
    mic.current?.stop()
    mic.current = null
    if (timer.current) clearTimeout(timer.current)
    const id = generation.current
    const body = wavFromPcm16(frames.current)
    frames.current = []
    const ctl = new AbortController()
    request.current = ctl
    setState('transcribing')
    timer.current = setTimeout(() => ctl.abort(), 60000)
    try {
      const result = await apiFetch<Schemas['MicTestOut']>('/api/voice/test-mic', {
        method: 'POST',
        body,
        headers: { 'Content-Type': 'audio/wav' },
        signal: ctl.signal,
      })
      if (generation.current === id && !ctl.signal.aborted) onTranscript(result.text)
    } catch (e) {
      if (generation.current === id)
        setError(ctl.signal.aborted ? 'Transcription timed out. Try again or type.' : (e as Error).message)
    } finally {
      if (generation.current === id) {
        if (timer.current) clearTimeout(timer.current)
        request.current = null
        setState('idle')
      }
    }
  }
  async function begin() {
    cleanup()
    const id = generation.current
    setError('')
    setState('opening')
    try {
      const opened = await startMic((frame) => {
        if (generation.current === id) frames.current.push(frame)
      })
      if (generation.current !== id) {
        opened.stop()
        return
      }
      mic.current = opened
      setState('recording')
      timer.current = setTimeout(() => void finish(), 18000)
    } catch (e) {
      if (generation.current === id) {
        setError((e as Error).message)
        setState('idle')
      }
    }
  }
  return (
    <div className="mt-2">
      <Button
        disabled={disabled || state === 'opening' || state === 'transcribing'}
        onClick={() => (state === 'recording' ? void finish() : void begin())}
      >
        {state === 'recording'
          ? 'Done — transcribe'
          : state === 'opening'
            ? 'Opening microphone…'
            : state === 'transcribing'
              ? 'Transcribing locally…'
              : 'Dictate question'}
      </Button>
      {state !== 'idle' && (
        <Button variant="ghost" onClick={cancel}>
          Cancel recording
        </Button>
      )}
      <p className="text-xs text-muted">Up to 18 seconds · review the text before sending.</p>
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
