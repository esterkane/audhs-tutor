import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { apiFetch, type Schemas } from '../../lib/api'
import { Player, b64ToPcm16 } from './audio'

export function ReadAloud({ text }: { text: string }) {
  const playback = useRef<Player | null>(null)
  const controller = useRef<AbortController | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
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
    setError('')
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
      }
      player.onIdle = () => {
        if (controller.current === ctl && !ctl.signal.aborted) setBusy(false)
      }
      if (!player.pending()) setBusy(false)
    } catch (e) {
      if (!ctl.signal.aborted) {
        setError((e as Error).message)
        stop()
      }
    }
  }
  return (
    <div className="mt-2">
      <Button size="sm" onClick={() => (busy ? stop() : void speak())} disabled={!text.trim()}>
        {busy ? 'Stop audio' : 'Listen to explanation'}
      </Button>
      <span className="text-xs text-muted ml-2">Local voice · no microphone · English voice</span>
      {error && (
        <p role="alert" className="text-sm mt-1">
          {error} <Link to="/models">Voice setup</Link>
        </p>
      )}
    </div>
  )
}
