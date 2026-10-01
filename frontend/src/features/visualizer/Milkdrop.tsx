import { useEffect, useRef } from 'react'
import type { AudioInput } from './audio'
import { milkdropPresets } from './milkdrop-presets'
import butterchurnModule from 'butterchurn'
const butterchurn = 'default' in butterchurnModule ? butterchurnModule.default : butterchurnModule
export default function Milkdrop({
  input,
  running,
  reduced,
  selected,
  snapshot,
  onFailure,
}: {
  input: AudioInput | null
  running: boolean
  reduced: boolean
  snapshot: number
  selected: number
  onFailure: (message: string) => void
}) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const instance = useRef<ReturnType<typeof butterchurn.createVisualizer> | null>(null)
  const failure = useRef(onFailure)
  useEffect(() => {
    failure.current = onFailure
  }, [onFailure])
  useEffect(() => {
    const element = canvas.current
    if (!element) return
    let own: AudioContext | undefined
    let observer: ResizeObserver | undefined
    let viewer: ReturnType<typeof butterchurn.createVisualizer> | undefined
    const lost = (event: Event) => {
      event.preventDefault()
      failure.current('Graphics context lost. Showing the graph visual; playback is preserved.')
    }
    element.addEventListener('webglcontextlost', lost)
    try {
      if (
        !element.getContext('webgl2', {
          alpha: false,
          antialias: false,
          depth: false,
          stencil: false,
          premultipliedAlpha: false,
          preserveDrawingBuffer: true,
        })
      )
        throw new Error('WebGL 2 is unavailable')
      const context = input?.context ?? (own = new AudioContext())
      viewer = butterchurn.createVisualizer(context, element, {
        width: 720,
        height: 320,
        pixelRatio: 1,
        textureRatio: 1,
      })
      instance.current = viewer
      if (input?.node) viewer.connectAudio(input.node)
      const resize = () => {
        const b = element.getBoundingClientRect()
        const width = Math.max(1, Math.round(b.width * Math.min(devicePixelRatio, 2)))
        const height = Math.max(1, Math.round(b.height * Math.min(devicePixelRatio, 2)))
        if (element.width !== width || element.height !== height) {
          element.width = width
          element.height = height
          try {
            viewer?.setRendererSize(width, height)
            viewer?.render()
          } catch {
            failure.current('Rich visual could not resize. Showing the graph visual; playback is preserved.')
          }
        }
      }
      observer = new ResizeObserver(resize)
      observer.observe(element)
      resize()
    } catch (e) {
      failure.current(
        `Rich visuals unavailable (${(e as Error).message}). Showing the graph visual; playback is preserved.`,
      )
    }
    return () => {
      observer?.disconnect()
      element.removeEventListener('webglcontextlost', lost)
      if (input?.node) viewer?.disconnectAudio(input.node)
      instance.current = null
      void own?.close().catch(() => {})
      window.setTimeout(() => {
        if (!element.isConnected)
          element.getContext('webgl2')?.getExtension('WEBGL_lose_context')?.loseContext()
      }, 0)
    }
  }, [input])
  useEffect(() => {
    if (!instance.current) return
    try {
      instance.current.loadPreset(milkdropPresets[selected].value, reduced ? 0 : 1.5)
      for (let frame = 0; frame < (reduced ? 12 : 1); frame++) instance.current.render()
    } catch {
      failure.current('This rich preset could not render. Showing the graph visual; playback is preserved.')
    }
  }, [selected, reduced, input])
  useEffect(() => {
    if (snapshot && reduced) {
      try {
        instance.current?.render()
      } catch {
        failure.current('Snapshot unavailable. Showing the graph visual.')
      }
    }
  }, [snapshot, reduced])
  useEffect(() => {
    if (!running || reduced) return
    let id = 0
    const tick = () => {
      try {
        instance.current?.render()
        id = requestAnimationFrame(tick)
      } catch {
        failure.current('Rich rendering stopped. Showing the graph visual; playback is preserved.')
      }
    }
    id = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(id)
  }, [running, reduced])
  return (
    <canvas
      ref={canvas}
      className="absolute inset-0 w-full h-full rounded"
      aria-label="MilkDrop visual preview"
    >
      MilkDrop artistic visual; not a frequency measurement.
    </canvas>
  )
}
