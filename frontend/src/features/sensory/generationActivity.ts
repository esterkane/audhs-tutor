import { useEffect } from 'react'
import { create } from 'zustand'
export const useGenerationActivity = create<{ count: number }>(() => ({ count: 0 }))
export function useGenerationBusy(busy: boolean) {
  useEffect(() => {
    if (!busy) return
    useGenerationActivity.setState(s => ({ count: s.count + 1 }))
    return () => useGenerationActivity.setState(s => ({ count: Math.max(0, s.count - 1) }))
  }, [busy])
}
