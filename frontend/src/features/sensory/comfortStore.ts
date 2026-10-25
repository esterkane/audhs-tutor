import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useComfort = create<{ focus: boolean; setFocus: (focus: boolean) => void }>()(
  persist(set => ({ focus: false, setFocus: focus => set({ focus }) }), { name: 'audhs-comfort' }),
)
