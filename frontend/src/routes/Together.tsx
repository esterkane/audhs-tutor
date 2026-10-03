import { claimReading, updateReading } from '../features/voice/readingOwner'
import { AudioControls } from '../features/audio/AudioControls'
import { bindOutput } from '../features/audio/settings'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Card, CardTitle } from '../components/ui/card'
import { useSensory } from '../features/sensory/useSensory'
import { routeForPhase, useCurrentSession } from '../features/session/api'
import { useMode } from '../stores/mode'

type AmbientAudio = {
  ctx: AudioContext
  node?: AudioBufferSourceNode
  releaseOutput?: () => void
  releaseOwner: () => void
}

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
  const [notice, setNotice] = useState('')
  const audio = useRef<AmbientAudio | null>(null)

  useEffect(() => {
    const id = setInterval(() => setMinutes(Math.floor((nowMs() - startedAt) / 60_000)), 15_000)
    return () => clearInterval(id)
  }, [startedAt])

  useEffect(() => () => stopSound(), [])
  useEffect(() => {
    if (ambient === 'off' && audio.current) stopSound() // preference switched off while playing
  }, [ambient])

  function startSound() {
    if (audio.current) return
    if (typeof AudioContext === 'undefined') {
      setNotice('Ambient sound is unavailable in this browser.')
      return
    }
    setNotice('')
    let instance: AmbientAudio | null = null
    try {
      const ctx = new AudioContext()
      instance = { ctx, releaseOwner: () => {} }
      audio.current = instance
      const current = instance
      current.releaseOwner = claimReading((replacement) => {
        stopSound(current)
        setNotice(`Brown noise stopped for ${replacement}. Choose Play brown noise to start again.`)
      }, 'brown noise')
      updateReading(current.releaseOwner, {
        kind: 'ambient',
        status: 'Starting brown noise',
        stop: () => stopSound(current),
      })
      const buffer = ctx.createBuffer(1, ctx.sampleRate * 4, ctx.sampleRate)
      const data = buffer.getChannelData(0)
      let last = 0
      for (let i = 0; i < data.length; i++) {
        const white = Math.random() * 2 - 1
        last = (last + 0.02 * white) / 1.02 // brown noise: integrated white noise
        data[i] = last * 3.5
      }
      const node = ctx.createBufferSource()
      current.node = node
      node.buffer = buffer
      node.loop = true
      const gain = ctx.createGain()
      current.releaseOutput = bindOutput(gain, 0.3)
      node.connect(gain).connect(ctx.destination)
      node.start()
      setPlaying(true)
      void ctx
        .resume()
        .then(() => {
          if (audio.current !== current) return
          updateReading(current.releaseOwner, {
            kind: 'ambient',
            status: 'Playing brown noise',
            stop: () => stopSound(current),
          })
        })
        .catch(() => {
          if (audio.current !== current) return
          stopSound(current)
          setNotice('Brown noise could not start. Choose Play brown noise to try again.')
        })
    } catch {
      if (instance) stopSound(instance)
      setNotice('Brown noise could not start. Choose Play brown noise to try again.')
    }
  }
  function stopSound(expected = audio.current) {
    if (!expected || audio.current !== expected) return
    audio.current = null
    expected.releaseOwner()
    expected.releaseOutput?.()
    try {
      expected.node?.stop()
    } catch {
      /* A source may fail before starting. */
    }
    void expected.ctx.close().catch(() => {})
    setPlaying(false)
  }

  const task = session.data?.active_skill?.title
  return (
    <div className="grid gap-4">
      <Card>
        <AudioControls />
        <CardTitle>Working alongside</CardTitle>
        <p className="text-2xl mt-2">
          {task ? `Now: ${task}` : session.data ? 'Current session' : 'No session running.'}
        </p>
        <p className="text-sm text-muted mt-1">
          {session.data
            ? `${mode.replace('_', ' ')} mode · ${minutes} min here`
            : 'Start a session from Home when ready.'}
        </p>
        <div className="flex flex-wrap gap-2 mt-4">
          {session.data ? (
            <Button variant="primary" asChild>
              <Link to={routeForPhase(session.data?.state)}>Back to the session</Link>
            </Button>
          ) : (
            <Button variant="primary" asChild>
              <Link to="/">Home</Link>
            </Button>
          )}
          {ambient !== 'off' &&
            (playing ? (
              <Button onClick={() => stopSound()}>Stop brown noise</Button>
            ) : (
              <Button onClick={startSound}>Play brown noise</Button>
            ))}
        </div>
        {notice && (
          <p role="status" className="mt-2">
            {notice}
          </p>
        )}
        <p className="text-sm text-muted mt-3">
          This is a quiet focus screen, not a live human companion. Nothing is scored here.
          {ambient === 'off' ? ' Ambient sound can be enabled under Preferences.' : ''}
        </p>
      </Card>
    </div>
  )
}
