import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { bindOutput, useAudioSettings } from './settings'

export function AudioControls() {
  const { volume, muted, rate, saved, update } = useAudioSettings()
  const cleanup = useRef<(() => void) | null>(null)
  const [status, setStatus] = useState('')
  useEffect(() => () => cleanup.current?.(), [])
  async function test() {
    cleanup.current?.()
    let ctx: AudioContext | undefined
    try {
      ctx = new AudioContext()
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      const unsubscribe = bindOutput(gain, 0.15)
      oscillator.frequency.value = 440
      oscillator.connect(gain).connect(ctx.destination)
      let closed = false
      const close = () => {
        if (closed) return
        closed = true
        unsubscribe()
        void ctx?.close().catch(() => {})
      }
      cleanup.current = close
      await ctx.resume()
      if (closed) return
      oscillator.start()
      oscillator.stop(ctx.currentTime + 0.5)
      setStatus('Playing a half-second test tone through your Mac’s selected output.')
      oscillator.onended = () => {
        close()
        setStatus('Test finished. If you heard nothing, check the Mac output and browser tab mute.')
      }
    } catch (e) {
      cleanup.current?.()
      void ctx?.close().catch(() => {})
      setStatus(`Sound test failed: ${(e as Error).message}`)
    }
  }
  return (
    <details className="my-2 text-sm rounded-lg border border-line p-2">
      <summary className="cursor-pointer">
        Audio controls · {muted || volume === 0 ? 'muted' : `${Math.round(volume * 100)}%`} · {rate}×
      </summary>
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
  )
}
