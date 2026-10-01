import type { Measurement } from './measurement'
export function LiveMeasurement({ value, still }: { value: Measurement | null; still: boolean }) {
  if (!value)
    return (
      <p className="text-sm">Start a test signal or play a file to see measured waveform and spectrum.</p>
    )
  const m = value
  const samples = m.wave.slice(0, Math.min(512, m.wave.length))
  const wave = samples
    .map((v, i) => `${(i / Math.max(1, samples.length - 1)) * 600},${60 - v * 100}`)
    .join(' ')
  const count = 150
  const points = Array.from({ length: count }, (_, i) => {
    const a = Math.floor((i * m.db.length) / count),
      b = Math.max(a + 1, Math.floor(((i + 1) * m.db.length) / count))
    const peak = Math.max(...m.db.slice(a, b))
    return `${(i / (count - 1)) * 600},${100 - Math.max(0, Math.min(100, peak + 100))}`
  }).join(' ')
  return (
    <section aria-label="Live audio measurements" className="grid gap-2">
      <h3 className="font-medium">Measured signal {still ? '· snapshot' : ''}</h3>
      <svg
        viewBox="0 0 600 120"
        role="img"
        aria-label="Waveform: digital amplitude over a short time window"
        className="w-full h-28 bg-slate-900 rounded"
      >
        <line x1="0" x2="600" y1="60" y2="60" stroke="#64748b" />
        <polyline points={wave} fill="none" stroke="#a78bfa" strokeWidth="2" />
      </svg>
      <p className="text-sm">
        Waveform window: {((samples.length / m.sampleRate) * 1000).toFixed(1)} ms. RMS digital amplitude:{' '}
        {m.rms.toFixed(3)}.
      </p>
      <svg
        viewBox="0 0 600 110"
        role="img"
        aria-label={`Spectrum: 0 to ${m.sampleRate / 2} Hz, minus 100 to 0 dBFS`}
        className="w-full h-28 bg-slate-900 rounded"
      >
        <polyline points={points} fill="none" stroke="#38bdf8" strokeWidth="2" />
      </svg>
      <p className="text-sm">
        Spectrum: 0–{m.sampleRate / 2} Hz · −100 to 0 dBFS. Strongest bin: {m.peakHz.toFixed(1)} Hz. Bin
        spacing: {(m.sampleRate / m.fftSize).toFixed(1)} Hz.
      </p>
      <p className="text-xs text-muted">
        Digital levels are not calibrated sound pressure or perceived loudness. Spectrum bins use a windowed
        FFT; displayed peak and amplitude are approximate.
      </p>
    </section>
  )
}
