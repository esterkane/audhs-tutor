import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Mode = 'novelty' | 'steady' | 'low_capacity'

/** Learner-selectable state (AuDHD UX invariant). Nothing here changes without a user action. */
export type ModeState = {
  mode: Mode
  energy: number
  socratic: boolean
  sessionId: string | null
  skillId: string | null
  reducedMotion: boolean
  setMode: (mode: Mode) => void
  setEnergy: (energy: number) => void
  setSocratic: (socratic: boolean) => void
  setSession: (sessionId: string | null, skillId?: string | null) => void
  setSkill: (skillId: string | null) => void
  reset: () => void
}

export const MODE_LABELS: Record<Mode, { title: string; hint: string }> = {
  novelty: { title: 'Novelty', hint: 'Fresh material, longer blocks.' },
  steady: { title: 'Steady', hint: 'Balanced: review, then one new idea.' },
  low_capacity: {
    title: 'Low capacity',
    hint: 'Shortest useful path: review + recap.',
  },
}

export const SOFT_TIMER_MIN: Record<Mode, number> = {
  novelty: 35,
  steady: 25,
  low_capacity: 15,
}

export const useMode = create<ModeState>()(
  persist(
    (set) => ({
      mode: 'steady',
      energy: 3,
      socratic: false,
      sessionId: null,
      skillId: null,
      reducedMotion:
        typeof window !== 'undefined' && typeof window.matchMedia === 'function'
          ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
          : false,
      setMode: (mode) => set({ mode }),
      setEnergy: (energy) => set({ energy }),
      setSocratic: (socratic) => set({ socratic }),
      setSession: (sessionId, skillId = null) => set({ sessionId, skillId }),
      setSkill: (skillId) => set({ skillId }),
      reset: () => set({ sessionId: null, skillId: null }),
    }),
    {
      name: 'audhs-mode',
      partialize: (s) => ({
        mode: s.mode,
        energy: s.energy,
        // `socratic` is deliberately not persisted: questioning style is an opt-in per session
        sessionId: s.sessionId,
        skillId: s.skillId,
      }),
    },
  ),
)
