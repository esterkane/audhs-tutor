import { features, type Frame } from './engine'
export type AudioInput = {
  read: () => Frame
  stop: () => void
  setAudible: (audible: boolean) => void
  pause?: () => void
  resume?: () => Promise<void>
  seek?: (seconds: number) => void
  setRepeat?: (range: { start: number; end: number } | null, onWrap?: () => void) => void
  position?: () => { seconds: number; duration: number }
}
/** The chosen file is a blob URL. No upload, recording, capture, model call or persistent audio. */
export async function openAudio(
  file: File,
  audible: boolean,
  signal: AbortSignal,
  onEnded: () => void = () => {},
): Promise<AudioInput> {
  if (file.size > 100 * 1024 * 1024) throw new Error('Choose an audio file smaller than 100 MiB.')
  const context = new AudioContext()
  const audio = new Audio()
  const url = URL.createObjectURL(file)
  let stopped = false
  let paused = false
  let operation = 0
  let repeat: { start: number; end: number } | null = null
  let onWrap = () => {}
  let lastPosition = { seconds: 0, duration: 0 }
  const position = () =>
    stopped
      ? lastPosition
      : {
          seconds: Number.isFinite(audio.currentTime) ? audio.currentTime : 0,
          duration: Number.isFinite(audio.duration) ? audio.duration : 0,
        }
  const stop = () => {
    if (stopped) return
    operation += 1
    lastPosition = position()
    stopped = true
    audio.pause()
    audio.removeAttribute('src')
    audio.load()
    URL.revokeObjectURL(url)
    signal.removeEventListener('abort', stop)
    audio.removeEventListener('ended', ended)
    audio.removeEventListener('timeupdate', checkRepeat)
    void context.close().catch(() => {})
  }
  const checkRepeat = () => {
    if (stopped || paused || !repeat) return
    if (audio.currentTime >= repeat.end || audio.currentTime < repeat.start) {
      audio.currentTime = repeat.start
      onWrap()
    }
  }
  const ended = () => {
    if (!stopped && !paused && repeat) {
      audio.currentTime = repeat.start
      onWrap()
      const attempt = ++operation
      void audio
        .play()
        .then(() => {
          if (attempt === operation && (stopped || paused)) audio.pause()
        })
        .catch(() => {
          if (attempt !== operation || stopped || paused) return
          stop()
          onEnded()
        })
      return
    }
    stop()
    onEnded()
  }
  audio.addEventListener('ended', ended)
  audio.addEventListener('timeupdate', checkRepeat)
  signal.addEventListener('abort', stop, { once: true })
  if (signal.aborted) {
    stop()
    throw new Error('Audio start cancelled.')
  }
  try {
    audio.src = url
    const source = context.createMediaElementSource(audio)
    const analyser = context.createAnalyser()
    const gain = context.createGain()
    analyser.fftSize = 2048
    analyser.smoothingTimeConstant = 0.5
    source.connect(analyser)
    analyser.connect(gain)
    gain.connect(context.destination)
    gain.gain.value = audible ? 0.5 : 0
    await context.resume()
    await audio.play()
    if (signal.aborted) throw new Error('Audio start cancelled.')
    const wave = new Float32Array(analyser.fftSize)
    const spectrum = new Float32Array(analyser.frequencyBinCount)
    return {
      position,
      setRepeat(range, wrap = () => {}) {
        if (stopped) return
        if (
          range &&
          (!Number.isFinite(range.start) ||
            !Number.isFinite(range.end) ||
            !Number.isFinite(audio.duration) ||
            range.start < 0 ||
            range.end > audio.duration ||
            range.end - range.start < 0.5)
        )
          throw new Error('Invalid repeat section.')
        repeat = range
        onWrap = wrap
        if (range) {
          audio.currentTime = range.start
          onWrap()
        }
      },
      pause() {
        if (!stopped) {
          operation += 1
          paused = true
          audio.pause()
        }
      },
      async resume() {
        if (stopped || signal.aborted) throw new Error('Playback has stopped. Press Play to start again.')
        const attempt = ++operation
        await context.resume()
        if (attempt !== operation || stopped || signal.aborted) return
        paused = false
        await audio.play()
        if (attempt === operation && (stopped || signal.aborted)) audio.pause()
      },
      seek(seconds) {
        if (stopped || !Number.isFinite(seconds) || !Number.isFinite(audio.duration)) return
        audio.currentTime = Math.max(0, Math.min(seconds, audio.duration))
      },
      read() {
        if (stopped || audio.ended) return { rms: 0, bass: 0, mid: 0, treble: 0 }
        analyser.getFloatTimeDomainData(wave)
        analyser.getFloatFrequencyData(spectrum)
        return features(wave, spectrum, context.sampleRate, analyser.fftSize)
      },
      stop,
      setAudible(value) {
        gain.gain.value = value ? 0.5 : 0
      },
    }
  } catch (e) {
    stop()
    throw e
  }
}
