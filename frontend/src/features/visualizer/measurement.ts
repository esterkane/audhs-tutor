export type Measurement = {
  wave: number[]
  db: number[]
  sampleRate: number
  fftSize: number
  rms: number
  peakHz: number
}
/** Digital samples and dBFS spectrum; intentionally separate from artistic normalized bands. */
export function measure(analyser: AnalyserNode): Measurement {
  const wave = new Float32Array(analyser.fftSize)
  const db = new Float32Array(analyser.frequencyBinCount)
  analyser.getFloatTimeDomainData(wave)
  analyser.getFloatFrequencyData(db)
  return summarize(wave, db, analyser.context.sampleRate, analyser.fftSize)
}
export function summarize(
  wave: Float32Array,
  db: Float32Array,
  sampleRate: number,
  fftSize: number,
): Measurement {
  let peak = 0
  for (let i = 1; i < db.length; i++) if (db[i] > db[peak]) peak = i
  return {
    wave: Array.from(wave),
    db: Array.from(db),
    sampleRate,
    fftSize,
    rms: Math.sqrt(wave.reduce((s, x) => s + x * x, 0) / Math.max(wave.length, 1)),
    peakHz: db[peak] > -100 ? (peak * sampleRate) / fftSize : 0,
  }
}
