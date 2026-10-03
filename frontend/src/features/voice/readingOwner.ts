import { create } from 'zustand'

type ReadingControls = {
  status: string
  paused: boolean
  changing: boolean
  ready: boolean
  stop: () => void
  togglePause: () => void
}
/** Ephemeral controls, scoped to requested readings in this tab. Never persisted. */
export const useReadingControls = create<{ reading: ReadingControls | null }>(() => ({ reading: null }))
let active: { stop: () => void; release: () => void } | null = null

export function claimReading(stop: () => void): () => void {
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
  previous?.stop()
  return owner.release
}

export function updateReading(release: () => void, controls: ReadingControls) {
  if (active?.release === release) useReadingControls.setState({ reading: controls })
}
