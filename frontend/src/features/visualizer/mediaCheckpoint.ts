// One tab-lifetime File reference, never persisted or uploaded. No live audio resources.
export type MediaCheckpoint = {
  file: File
  position: { seconds: number; duration: number }
  repeat: { start: number; end: number } | null
  resume: boolean
}
let checkpoint: MediaCheckpoint | null = null
export const mediaCheckpoint = {
  read: () => checkpoint,
  write: (value: MediaCheckpoint | null) => { checkpoint = value },
}
