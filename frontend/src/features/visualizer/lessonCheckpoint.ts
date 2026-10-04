import { defaultTone, type ToneSettings } from './tone'
export const lessonIds = ['amplitude', 'frequency', 'harmonics', 'sampling', 'mapping', 'create'] as const
export type LessonCheckpoint = { step: typeof lessonIds[number]; settings: ToneSettings; hint: boolean }
export const initialLesson: LessonCheckpoint = { step: 'amplitude', settings: defaultTone, hint: false }
export function parseLesson(value: unknown): LessonCheckpoint {
  const state = value as LessonCheckpoint
  const settings = state?.settings
  if (!state || !lessonIds.includes(state.step) || typeof state.hint !== 'boolean' || !settings ||
      !Number.isFinite(settings.frequency) || settings.frequency < 100 || settings.frequency > 1000 ||
      !Number.isFinite(settings.amplitude) || settings.amplitude < 0 || settings.amplitude > 0.5 ||
      !['sine', 'square'].includes(settings.waveform) || ![512, 2048, 8192].includes(settings.fftSize))
    throw new Error('Invalid lesson checkpoint')
  return { step: state.step, hint: state.hint, settings: { frequency: settings.frequency, amplitude: settings.amplitude, waveform: settings.waveform, fftSize: settings.fftSize } }
}
