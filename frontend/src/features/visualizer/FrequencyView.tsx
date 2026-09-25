import { useEffect, useRef, useState } from 'react'
import type WaveSurfer from 'wavesurfer.js'

/** Reuses the existing 4 kHz overview buffer: no second audio decoder or player. */
export function FrequencyView({ player, duration }: { player: WaveSurfer; duration: number }) {
  const container = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState('Preparing frequency view locally…')
  useEffect(() => {
    let disposed = false
    let destroy: (() => void) | undefined
    void import('wavesurfer.js/dist/plugins/spectrogram.js')
      .then(({ default: Spectrogram }) => {
        if (disposed || !container.current) return
        const plugin = Spectrogram.create({
          container: container.current,
          height: 160,
          labels: true,
          labelsBackground: '#111827',
          labelsColor: '#ffffff',
          labelsHzColor: '#ffffff',
          frequencyMin: 0,
          frequencyMax: 2000,
          scale: 'linear',
          fftSamples: 512,
          noverlap: 256,
          colorMap: 'igray',
          gainDB: 20,
          rangeDB: 80,
          useWebWorker: true,
          fallbackToMainThread: false,
        })
        destroy = () => plugin.destroy()
        plugin.on('ready', () => {
          if (!disposed) setStatus('Frequency view ready.')
        })
        plugin.on('error', () => {
          if (!disposed) setStatus('Frequency view unavailable. Waveform and playback still work.')
        })
        player.registerPlugin(plugin)
      })
      .catch(() => {
        if (!disposed) setStatus('Frequency view unavailable. Waveform and playback still work.')
      })
    return () => {
      disposed = true
      destroy?.()
    }
  }, [player])
  return (
    <section aria-label="Low-frequency spectrogram" className="grid gap-2 border border-line rounded p-3">
      <h3 className="font-medium">Where lower frequencies appear</h3>
      <p className="text-sm">
        Left to right is time. Bottom to top is frequency (Hz). Brighter areas mean stronger frequency
        components on this fixed display scale; the waveform overview does not separate individual
        frequencies.
      </p>
      <div
        ref={container}
        role="img"
        aria-label="Spectrogram: time runs left to right; frequency rises from 0 to 2000 Hz; lighter shades mean stronger components"
      />
      <div className="flex justify-between text-xs" aria-label="Time axis">
        <span>0 s</span>
        <span>{(duration / 2).toFixed(1)} s</span>
        <span>{duration.toFixed(1)} s</span>
      </div>
      <p role="status" className="text-sm">
        {status}
      </p>
      <p className="text-sm">
        This lightweight overview covers only 0–2,000 Hz. It leaves out higher frequencies, including much of
        the treble. It cannot identify instruments or tell you whether a sound is good.
      </p>
      <details>
        <summary className="cursor-pointer">Try one comparison</summary>
        <p className="text-sm mt-2">
          Look for a horizontal band: energy stays near one frequency over time. A brief vertical band spans
          several frequencies at one moment. Compare the same passage using Repeat a short section. These
          patterns alone do not identify their cause.
        </p>
      </details>
    </section>
  )
}
