import { create } from 'zustand'

type Settings = { volume: number; rate: number; muted: boolean }
const defaults: Settings = { volume: 0.5, rate: 1, muted: false }
function read(): Settings {
  try {
    const value = JSON.parse(localStorage.getItem('audio-settings-v1') ?? '{}') as Partial<Settings>
    return {
      volume:
        typeof value.volume === 'number' && Number.isFinite(value.volume)
          ? Math.max(0, Math.min(1, value.volume))
          : defaults.volume,
      rate:
        typeof value.rate === 'number' && Number.isFinite(value.rate)
          ? Math.max(0.5, Math.min(2, value.rate))
          : defaults.rate,
      muted: typeof value.muted === 'boolean' ? value.muted : false,
    }
  } catch {
    return defaults
  }
}
export const useAudioSettings = create<
  Settings & { saved: boolean; update: (value: Partial<Settings>) => void }
>((set, get) => ({
  ...read(),
  saved: true,
  update(value) {
    const current = get()
    const next = { volume: current.volume, rate: current.rate, muted: current.muted, ...value }
    let saved = true
    try {
      localStorage.setItem('audio-settings-v1', JSON.stringify(next))
    } catch {
      saved = false
    }
    set({ ...next, saved })
  },
}))
/** Only monitor output changes: measurements and sensory opt-in stay independent. */
export function bindOutput(gain: GainNode, scale = 1) {
  const apply = () => {
    const s = useAudioSettings.getState()
    gain.gain.value = s.muted ? 0 : s.volume * scale
  }
  apply()
  return useAudioSettings.subscribe(apply)
}
export function bindMedia(audio: HTMLMediaElement) {
  const apply = () => {
    const s = useAudioSettings.getState()
    audio.volume = s.volume
    audio.muted = s.muted
    audio.playbackRate = s.rate
  }
  apply()
  return useAudioSettings.subscribe(apply)
}
