import { claimReading, updateReading, useReadingControls } from '../voice/readingOwner'
import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { bindOutput, useAudioSettings } from './settings'

const ACTIVITY_LABELS = {
  reading: 'Current reading',
  clip: 'Listening clip',
  voice: 'Voice activity',
  ambient: 'Ambient sound',
  test: 'Sound test',
  visualizer: 'Visualizer sound',
}
const STOP_LABELS = {
  reading: 'Stop reading',
  clip: 'Stop clip',
  voice: 'Stop voice activity',
  ambient: 'Stop ambient sound',
  test: 'Stop sound test',
  visualizer: 'Stop visualizer sound',
}

export function AudioControls({ compact = false }: { compact?: boolean }) {
  const reading = useReadingControls((s) => s.reading)
  const { volume, muted, rate, saved, update } = useAudioSettings()
  const summary = useRef<HTMLElement>(null)
  const cleanup = useRef<(() => void) | null>(null)
  const [status, setStatus] = useState('')
  useEffect(() => () => cleanup.current?.(), [])
  async function test() {
    cleanup.current?.()
    let ctx: AudioContext | undefined
    let oscillator: OscillatorNode | undefined
    let unsubscribe: (() => void) | undefined
    let release: (() => void) | undefined
    let closed = false
    let started = false
    const close = () => {
      if (closed) return
      closed = true
      if (oscillator) {
        oscillator.onended = null
        if (started) {
          try {
            oscillator.stop()
          } catch {
            // The half-second tone may already have ended.
          }
        }
      }
      unsubscribe?.()
      release?.()
      void ctx?.close().catch(() => {})
      if (cleanup.current === close) cleanup.current = null
    }
    cleanup.current = close
    const announce = (message: string) => {
      if (closed || !release) return
      setStatus(message)
      updateReading(release, {
        kind: 'test',
        status: message,
        stop: () => {
          close()
          setStatus('Sound test stopped.')
        },
      })
    }
    try {
      ctx = new AudioContext()
      oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      unsubscribe = bindOutput(gain, 0.15)
      oscillator.frequency.value = 440
      oscillator.connect(gain).connect(ctx.destination)
      release = claimReading((replacement) => {
        close()
        setStatus(`Sound test stopped because ${replacement} started.`)
      }, 'a sound test')
      announce('Preparing sound test…')
      await ctx.resume()
      if (closed) return
      oscillator.onended = () => {
        if (closed) return
        close()
        setStatus('Test finished. If you heard nothing, check the Mac output and browser tab mute.')
      }
      oscillator.start()
      started = true
      oscillator.stop(ctx.currentTime + 0.5)
      announce('Playing a half-second test tone through your Mac’s selected output.')
    } catch (e) {
      if (closed) return
      close()
      setStatus(`Sound test failed: ${(e as Error).message}`)
    }
  }
  const activity = reading && (
    <div className="mt-2 border-b border-line pb-2">
      <p>
        {ACTIVITY_LABELS[reading.kind ?? 'reading']}: {reading.status}
      </p>
      <div className="flex flex-wrap gap-2 mt-1">
        {'togglePause' in reading && reading.ready && (
          <Button size="sm" disabled={reading.changing} onClick={reading.togglePause}>
            {reading.kind === 'clip'
              ? reading.changing
                ? 'Starting clip…'
                : reading.paused
                  ? 'Resume clip'
                  : 'Pause clip'
              : reading.changing
                ? 'Updating reading…'
                : reading.paused
                  ? 'Resume reading'
                  : 'Pause reading'}
          </Button>
        )}
        <Button
          size="sm"
          onClick={() => {
            reading.stop()
            if (compact) summary.current?.focus()
          }}
        >
          {STOP_LABELS[reading.kind ?? 'reading']}
        </Button>
      </div>
    </div>
  )
  return (
    <div className="min-w-0 max-w-full">
      {compact && activity}
      <details className="my-2 text-sm rounded-lg border border-line p-2">
        <summary ref={summary} className="cursor-pointer">
          Audio controls
          {compact
            ? muted || volume === 0
              ? ' · muted'
              : ''
            : ` · ${muted || volume === 0 ? 'muted' : `${Math.round(volume * 100)}%`} · ${rate}×`}
        </summary>
        {!compact && activity}
        <div className="flex flex-wrap items-center gap-3 mt-2">
          <label>
            Volume {Math.round(volume * 100)}%{' '}
            <input
              aria-label="Audio volume"
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={volume}
              onChange={(e) => update({ volume: Number(e.target.value) })}
            />
          </label>
          <Button size="sm" aria-pressed={muted} onClick={() => update({ muted: !muted })}>
            {muted ? 'Unmute' : 'Mute'}
          </Button>
          <label>
            Playback speed{' '}
            <select value={rate} onChange={(e) => update({ rate: Number(e.target.value) })}>
              {[0.5, 0.75, 1, 1.25, 1.5, 1.75, 2].map((n) => (
                <option key={n} value={n}>
                  {n}×
                </option>
              ))}
            </select>
          </label>
          <Button size="sm" disabled={muted || volume === 0} onClick={() => void test()}>
            Test sound
          </Button>
        </div>
        <p className="text-xs text-muted mt-2">
          Shared across this app. Voice speed applies to the next spoken response and also changes pitch. File
          playback updates immediately. Test signals and ambient sound keep their original speed.
        </p>
        <p className="text-xs text-muted">
          Output: your Mac’s selected device. For Bluetooth headphones, select them in macOS Control Center →
          Sound; also check the browser tab is not muted. Visualizer sound must be enabled separately.
        </p>
        {status && <p role="status">{status}</p>}
        {!saved && <p role="alert">Settings work for now but could not be saved in this browser.</p>}
      </details>
    </div>
  )
}
