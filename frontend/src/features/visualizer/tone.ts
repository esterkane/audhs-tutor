import type { AudioInput } from './audio'
import { features } from './engine'
import { measure } from './measurement'
export type ToneSettings = {
  frequency: number
  amplitude: number
  waveform: 'sine' | 'square'
  fftSize: number
}
export const defaultTone: ToneSettings = { frequency: 220, amplitude: 0.2, waveform: 'sine', fftSize: 2048 }
export async function openTone(settings: ToneSettings, signal: AbortSignal): Promise<AudioInput> {
  const context = new AudioContext()
  const oscillator = context.createOscillator()
  const level = context.createGain()
  const analyser = context.createAnalyser()
  const monitor = context.createGain()
  let stopped = false
  const update = (s: ToneSettings) => {
    oscillator.type = s.waveform
    oscillator.frequency.value = Math.max(100, Math.min(1000, s.frequency))
    level.gain.value = Math.max(0, Math.min(0.5, s.amplitude))
    analyser.fftSize = [512, 2048, 8192].includes(s.fftSize) ? s.fftSize : 2048
    analyser.smoothingTimeConstant = 0
  }
  update(settings)
  monitor.gain.value = 0
  oscillator.connect(level)
  level.connect(analyser)
  analyser.connect(monitor)
  monitor.connect(context.destination)
  const stop = () => {
    if (stopped) return
    stopped = true
    oscillator.stop()
    signal.removeEventListener('abort', stop)
    void context.close().catch(() => {})
  }
  oscillator.start()
  signal.addEventListener('abort', stop, { once: true })
  try {
    if (signal.aborted) throw new Error('Tone start cancelled.')
    await context.resume()
    if (signal.aborted) throw new Error('Tone start cancelled.')
    return {
      visualizerId: crypto.randomUUID(),
      context,
      node: analyser,
      measurement: () => measure(analyser),
      updateTone: update,
      read: () => {
        const m = measure(analyser)
        return features(new Float32Array(m.wave), new Float32Array(m.db), m.sampleRate, m.fftSize)
      },
      stop,
      pause: () => {
        void context.suspend().catch(() => {})
      },
      resume: async () => {
        if (!stopped) await context.resume()
      },
      setAudible: (value) => {
        monitor.gain.value = value ? 0.5 : 0
      },
    }
  } catch (e) {
    stop()
    throw e
  }
}
