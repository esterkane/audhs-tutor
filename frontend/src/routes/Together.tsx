import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useSensory } from '../features/sensory/useSensory'
import { useCurrentSession } from '../features/session/api'
import { useMode } from '../stores/mode'

function nowMs() {
  return Date.now()
}

/** Body-doubling: a presence screen. It shows the one thing you are doing and stays quiet.
 *  Optional ambient sound is opt-in (preference) and starts only on a click. No tracking. */
export function Together() {
  const session = useCurrentSession()
  const { mode } = useMode()
  const { ambient } = useSensory()
  const [startedAt] = useState(() => nowMs())
  const [minutes, setMinutes] = useState(0)
  const [playing, setPlaying] = useState(false)
  const audio = useRef<{ ctx: AudioContext; node: AudioBufferSourceNode } | null>(null)

  useEffect(() => {
    const id = setInterval(() => setMinutes(Math.floor((nowMs() - startedAt) / 60_000)), 15_000)
    return () => clearInterval(id)
  }, [startedAt])

  useEffect(() => () => stopSound(), [])
  useEffect(() => {
    if (ambient === 'off' && audio.current) stopSound() // preference switched off while playing
  }, [ambient])

  function startSound() {
    if (typeof AudioContext === 'undefined') return
    const ctx = new AudioContext()
    const seconds = 4
    const buffer = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate)
    const data = buffer.getChannelData(0)
    let last = 0
    for (let i = 0; i < data.length; i++) {
      const white = Math.random() * 2 - 1
      last = (last + 0.02 * white) / 1.02 // brown noise: integrated white noise
      data[i] = last * 3.5
    }
    const node = ctx.createBufferSource()
    node.buffer = buffer
    node.loop = true
    const gain = ctx.createGain()
    gain.gain.value = 0.15
    node.connect(gain).connect(ctx.destination)
    node.start()
    audio.current = { ctx, node }
    setPlaying(true)
  }
  function stopSound() {
    audio.current?.node.stop()
    void audio.current?.ctx.close()
    audio.current = null
    setPlaying(false)
  }

  const task = session.data?.next_skill?.title
  return (
    <div className="grid gap-4">
      <Card>
        <CardTitle>Working alongside</CardTitle>
        <p className="text-2xl mt-2">{task ? `Now: ${task}` : 'No session running.'}</p>
        <p className="text-sm text-muted mt-1">
          {session.data
            ? `${mode.replace('_', ' ')} mode · ${minutes} min here`
            : 'Start a session from Home when ready.'}
        </p>
        <div className="flex flex-wrap gap-2 mt-4">
          {session.data ? (
            <Button variant="primary" asChild>
              <Link to="/session">Back to the session</Link>
            </Button>
          ) : (
            <Button variant="primary" asChild>
              <Link to="/">Home</Link>
            </Button>
          )}
          {ambient !== 'off' &&
            (playing ? (
              <Button onClick={stopSound}>Stop brown noise</Button>
            ) : (
              <Button onClick={startSound}>Play brown noise</Button>
            ))}
        </div>
        <p className="text-sm text-muted mt-3">
          This screen keeps you company: nothing is timed, tracked or scored here.
          {ambient === 'off' ? ' Ambient sound can be enabled under Preferences.' : ''}
        </p>
      </Card>
    </div>
  )
}
