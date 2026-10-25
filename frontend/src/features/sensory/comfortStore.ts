import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type BreakDesign = 'off' | 'frost' | 'liquid'
export const useComfort = create<{
  focus: boolean
  setFocus: (focus: boolean) => void
  breakDesign: BreakDesign
  setBreakDesign: (breakDesign: BreakDesign) => void
}>()(
  persist(set => ({
    focus: false, setFocus: focus => set({ focus }),
    breakDesign: 'off', setBreakDesign: breakDesign => set({ breakDesign }),
  }), { name: 'audhs-comfort' }),
)
