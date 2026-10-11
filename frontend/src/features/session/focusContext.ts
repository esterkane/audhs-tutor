import { createContext } from 'react'

export const LessonFocusContext = createContext<{ active: boolean; setActive: (active: boolean) => void } | null>(null)
