/** Browser audio helpers for the voice loop: microphone → PCM16 16 kHz frames, PCM playback queue,
 *  WAV encoding for the setup test. All start only on a learner action (no autoplay). */

export const MIC_RATE = 16_000

export function downsampleTo16k(input: Float32Array, inputRate: number): Int16Array {
  const ratio = inputRate / MIC_RATE
  const n = Math.floor(input.length / ratio)
  const out = new Int16Array(n)
  for (let i = 0; i < n; i++) {
    const start = Math.floor(i * ratio)
    const end = Math.min(input.length, Math.floor((i + 1) * ratio))
    let sum = 0
    for (let j = start; j < end; j++) sum += input[j]
    const v = end > start ? sum / (end - start) : 0
    out[i] = Math.max(-32768, Math.min(32767, Math.round(v * 32767)))
  }
  return out
}

export function wavFromPcm16(frames: Int16Array[], rate = MIC_RATE): Blob {
  const total = frames.reduce((n, f) => n + f.length, 0)
  const buf = new ArrayBuffer(44 + total * 2)
  const v = new DataView(buf)
  const str = (o: number, s: string) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)))
  str(0, 'RIFF')
  v.setUint32(4, 36 + total * 2, true)
  str(8, 'WAVE')
  str(12, 'fmt ')
  v.setUint32(16, 16, true)
  v.setUint16(20, 1, true)
  v.setUint16(22, 1, true)
  v.setUint32(24, rate, true)
  v.setUint32(28, rate * 2, true)
  v.setUint16(32, 2, true)
  v.setUint16(34, 16, true)
  str(36, 'data')
  v.setUint32(40, total * 2, true)
  let o = 44
  for (const f of frames) {
    for (let i = 0; i < f.length; i++, o += 2) v.setInt16(o, f[i], true)
  }
  return new Blob([buf], { type: 'audio/wav' })
}

export type Mic = { stop: () => void }

/** Start capturing; `onFrame` gets ~100 ms PCM16 frames at 16 kHz. Throws when there is no mic. */
export async function startMic(onFrame: (pcm: Int16Array) => void): Promise<Mic> {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
    throw new Error('This browser has no microphone access (getUserMedia). Use text instead.')
  }
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { channelCount: 1, echoCancellation: true },
  })
  const ctx = new AudioContext()
  const source = ctx.createMediaStreamSource(stream)
  const proc = ctx.createScriptProcessor(4096, 1, 1)
  proc.onaudioprocess = (e) => onFrame(downsampleTo16k(e.inputBuffer.getChannelData(0), ctx.sampleRate))
  source.connect(proc)
  proc.connect(ctx.destination)
  return {
    stop: () => {
      proc.disconnect()
      source.disconnect()
      stream.getTracks().forEach((t) => t.stop())
      void ctx.close()
    },
  }
}

/** Plays PCM16 chunks back to back; `stop()` cuts playback immediately (interruption). */
export class Player {
  private ctx: AudioContext | null = null
  private nextAt = 0
  private sources: AudioBufferSourceNode[] = []

  onIdle: (() => void) | null = null

  pending(): number {
    return this.sources.length
  }

  async unlock() {
    if (typeof AudioContext === 'undefined') throw new Error('Audio playback is unavailable in this browser.')
    this.ctx = this.ctx ?? new AudioContext()
    if (this.ctx.state === 'suspended') await this.ctx.resume()
  }

  enqueue(pcm16: Int16Array, sampleRate: number) {
    if (typeof AudioContext === 'undefined') return
    this.ctx = this.ctx ?? new AudioContext()
    if (this.ctx.state === 'suspended') void this.ctx.resume() // Safari keeps fresh contexts suspended
    const buffer = this.ctx.createBuffer(1, pcm16.length, sampleRate)
    const data = buffer.getChannelData(0)
    for (let i = 0; i < pcm16.length; i++) data[i] = pcm16[i] / 32768
    const node = this.ctx.createBufferSource()
    node.buffer = buffer
    node.connect(this.ctx.destination)
    const at = Math.max(this.ctx.currentTime, this.nextAt)
    node.start(at)
    this.nextAt = at + buffer.duration
    this.sources.push(node)
    node.onended = () => {
      this.sources = this.sources.filter((s) => s !== node)
      if (this.sources.length === 0) this.onIdle?.()
    }
  }

  stop() {
    for (const s of this.sources) {
      try {
        s.stop()
      } catch {
        /* already ended */
      }
    }
    this.sources = []
    this.nextAt = 0
  }

  close() {
    this.stop()
    void this.ctx?.close()
    this.ctx = null
  }
}

export function b64ToPcm16(b64: string): Int16Array {
  const bin = atob(b64)
  const bytes = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i)
  return new Int16Array(bytes.buffer, 0, Math.floor(bytes.length / 2))
}
