import { useEffect, useRef, useState } from 'react'
import WaveSurfer from 'wavesurfer.js'
import { Button } from '../../components/ui/button'
import { FrequencyView } from './FrequencyView'

/** Visual-only local file preview; never owns playback or uploads the file. */
export function AudioWaveform({ file, seconds, reduced }: { file: File; seconds: number; reduced: boolean }) {
  const container = useRef<HTMLDivElement>(null)
  const wave = useRef<WaveSurfer | null>(null)
  const [loaded, setLoaded] = useState<{
    file: File
    player: WaveSurfer | null
    duration: number
    status: string
  } | null>(null)
  const [frequencyFile, setFrequencyFile] = useState<File | null>(null)
  const current = loaded?.file === file ? loaded : null
  const readyPlayer = current?.player ?? null
  const duration = current?.duration ?? 0
  const status = current?.status ?? 'Preparing waveform locally…'
  const showFrequency = frequencyFile === file
  useEffect(() => {
    if (!container.current) return
    if (file.size > 20 * 1024 * 1024) return
    let disposed = false
    const player = WaveSurfer.create({
      container: container.current,
      height: 72,
      waveColor: '#64748b',
      progressColor: '#7c3aed',
      cursorWidth: 0,
      interact: false,
      autoplay: false,
      sampleRate: 4000,
    })
    player.setMuted(true)
    wave.current = player
    const unsubscribe = player.on('error', () => {
      if (!disposed)
        setLoaded({
          file,
          player: null,
          duration: 0,
          status: 'Waveform unavailable. You can still try playing this file.',
        })
    })
    void player
      .loadBlob(file)
      .then(() => {
        if (!disposed) {
          setLoaded({
            file,
            player,
            duration: player.getDuration(),
            status: `Waveform ready · duration ${player.getDuration().toFixed(1)} seconds.`,
          })
        }
      })
      .catch(() => {
        if (!disposed)
          setLoaded({
            file,
            player: null,
            duration: 0,
            status: 'Waveform unavailable. You can still try playing this file.',
          })
      })
    return () => {
      disposed = true
      unsubscribe()
      wave.current = null
      player.destroy()
    }
  }, [file])
  useEffect(() => {
    if (!reduced) wave.current?.setTime(seconds)
  }, [seconds, reduced])
  if (file.size > 20 * 1024 * 1024)
    return (
      <p className="text-sm">
        Waveform preview is available for files up to 20 MiB. Playback supports files up to 100 MiB.
      </p>
    )
  return (
    <div className="grid gap-1">
      <div ref={container} role="img" aria-label={`Waveform overview of ${file.name}`} />
      <p role="status" className="text-sm">
        {status}
      </p>
      <Button
        variant="outline"
        disabled={!duration || duration > 120}
        aria-expanded={showFrequency}
        onClick={() => setFrequencyFile(showFrequency ? null : file)}
      >
        {showFrequency ? 'Hide frequency view' : 'Show frequency view (optional)'}
      </Button>
      {duration > 120 && (
        <p className="text-xs text-muted">
          Frequency view is limited to files up to 2 minutes to keep this local preview responsive.
        </p>
      )}
      {showFrequency && readyPlayer && <FrequencyView player={readyPlayer} duration={duration} />}
      <p className="text-xs text-muted">
        The waveform shows amplitude over the whole file. It is an overview, not an editable timeline.{' '}
        {reduced
          ? 'The waveform stays still because reduced motion is on.'
          : 'Purple marks playback progress.'}
      </p>
    </div>
  )
}
