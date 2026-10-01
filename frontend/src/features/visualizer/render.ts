import type { Preset } from './engine'
export function draw(canvas: HTMLCanvasElement, preset: Preset, scale: number, energy: number) {
  const c = canvas.getContext('2d')
  if (!c) return
  const w = canvas.width
  const h = canvas.height
  c.fillStyle = '#111827'
  c.fillRect(0, 0, w, h)
  c.strokeStyle = preset.visual.color
  c.fillStyle = preset.visual.color
  c.lineWidth = 3
  const radius = Math.min(w, h) * 0.17 * scale
  if (preset.visual.kind === 'rings') {
    for (let i = 1; i <= 4; i++) {
      c.beginPath()
      c.arc(w / 2, h / 2, (radius * i) / 3, 0, Math.PI * 2)
      c.stroke()
    }
  } else if (preset.visual.kind === 'bars') {
    for (let i = 0; i < 16; i++) {
      const height = (0.15 + energy * (0.3 + Math.sin(i * 0.7) ** 2)) * h * 0.3 * scale
      c.fillRect((w * (i + 1)) / 18, (h - height) / 2, w / 28, height)
    }
  } else {
    for (let i = 0; i < 10; i++) {
      const angle = (i * Math.PI) / 5 + energy * Math.PI
      c.beginPath()
      c.arc(
        w / 2 + Math.cos(angle) * radius,
        h / 2 + Math.sin(angle) * radius,
        4 + energy * 6,
        0,
        Math.PI * 2,
      )
      c.fill()
    }
  }
}
