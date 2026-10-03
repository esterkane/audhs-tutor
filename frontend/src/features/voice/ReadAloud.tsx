import { useAudioSettings } from '../audio/settings'
import { AudioControls } from '../audio/AudioControls'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { apiFetch, type Schemas } from '../../lib/api'
import { Player, b64ToPcm16 } from './audio'

export function ReadAloud(props: { text: string; label?: string }) {
  return <Speech key={props.text} {...props} />
}
function Speech({ text, label = 'Listen to explanation' }: { text: string; label?: string }) {
  const playback = useRef<Player | null>(null)
  const controller = useRef<AbortController | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const muted = useAudioSettings((s) => s.muted)
  const volume = useAudioSettings((s) => s.volume)
  useEffect(
    () => () => {
      controller.current?.abort()
      if (playback.current) playback.current.onIdle = null
      playback.current?.close()
    },
    [text],
  )
  function stop() {
    controller.current?.abort()
    if (playback.current) playback.current.onIdle = null
    playback.current?.close()
    playback.current = null
    setBusy(false)
  }
  async function speak() {
    stop()
    const ctl = new AbortController()
    controller.current = ctl
    const player = new Player()
    playback.current = player
    setBusy(true)
    setStatus('Preparing audio…')
    setError('')
    let synthesisFinished = false
    player.onIdle = () => {
      if (controller.current !== ctl || ctl.signal.aborted) return
      if (synthesisFinished) {
        setBusy(false)
        setStatus('Audio finished.')
        player.onIdle = null
        player.close()
        playback.current = null
      } else {
        setStatus('Preparing the next passage…')
      }
    }
    try {
      await player.unlock()
      // Each bounded passage is spoken completely; longer explanations are not silently truncated.
      const plain = text.replace(/\[([^\]]+)\]\([^)]*\)/g, '$1').replace(/[*#`]/g, '')
      const passages = plain.match(/[\s\S]{1,1000}(?:\s|$)|[\s\S]{1,1000}/g) ?? []
      for (const passage of passages) {
        if (ctl.signal.aborted) return
        const audio = await apiFetch<Schemas['SpeakOut']>('/api/voice/speak', {
          method: 'POST',
          body: JSON.stringify({ text: passage }),
          signal: ctl.signal,
        })
        if (ctl.signal.aborted) return
        player.enqueue(b64ToPcm16(audio.pcm16_b64), audio.sample_rate)
        setStatus('Audio playback in progress.')
      }
      synthesisFinished = true
      if (!player.pending()) player.onIdle?.()
    } catch (e) {
      if (!ctl.signal.aborted) {
        setError((e as Error).message)
        setStatus('Audio could not finish.')
        stop()
      }
    }
  }
  return (
    <div className="mt-2">
      <Button
        size="sm"
        onClick={() => {
          if (busy) {
            stop()
            setStatus('Audio stopped. Listen again starts from the beginning.')
          } else void speak()
        }}
        disabled={!text.trim()}
      >
        {busy ? 'Stop audio' : label}
      </Button>
      <p role="status" className="text-sm mt-1">
        {status}
      </p>
      {(muted || volume === 0) && (
        <p className="text-sm mt-1">
          {muted ? 'Audio is muted.' : 'Audio volume is zero.'} Open Audio controls to adjust playback.
        </p>
      )}
      <AudioControls />
      <span className="text-xs text-muted ml-2">Local voice · no microphone · English voice</span>
      {error && (
        <p role="alert" className="text-sm mt-1">
          {error} <Link to="/models">Voice setup</Link>
        </p>
      )}
    </div>
  )
}
