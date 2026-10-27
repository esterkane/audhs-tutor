import { createContext, useContext } from 'react'
type Focus = { loaded: boolean; error: boolean; cutoff: string | null }
export const FocusContext = createContext<Focus>({ loaded: true, error: false, cutoff: null })
export const useFocusPolicy = () => useContext(FocusContext)
