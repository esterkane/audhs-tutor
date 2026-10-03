import { create } from 'zustand'

type ReadingControls = {
  kind?: 'reading' | 'clip'
  status: string
  paused: boolean
  changing: boolean
  ready: boolean
  stop: () => void
  togglePause: () => void
}
type StopOnlyControls = {
  kind: 'voice' | 'ambient' | 'test' | 'visualizer'
  status: string
  stop: () => void
}
/** Ephemeral foreground audio activity in this tab. Never persisted. */
export const useReadingControls = create<{ reading: ReadingControls | StopOnlyControls | null }>(() => ({
  reading: null,
}))
let active: { stop: (replacement: string) => void; release: () => void } | null = null

export function claimReading(stop: (replacement: string) => void, label = 'another reading'): () => void {
  const previous = active
  const owner = {
    stop,
    release: () => {
      if (active === owner) {
        active = null
        useReadingControls.setState({ reading: null })
      }
    },
  }
  active = owner
  useReadingControls.setState({ reading: null })
  previous?.stop(label)
  return owner.release
}

export function updateReading(release: () => void, controls: ReadingControls | StopOnlyControls) {
  if (active?.release === release) useReadingControls.setState({ reading: controls })
}
