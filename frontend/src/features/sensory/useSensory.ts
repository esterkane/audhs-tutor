import { useEffect } from 'react'
import { usePreferences } from '../preferences/api'
import { useMode } from '../../stores/mode'

/** Applies the sensory preferences to the document: theme, density, text size, motion.
 *  `prefers-reduced-motion` is honoured regardless; the preference can only add restraint. */
export function useSensory() {
  const prefs = usePreferences()
  const systemReduced = useMode((s) => s.reducedMotion)
  const values = (prefs.data?.values ?? {}) as Record<string, unknown>
  const theme = String(values['ui.theme'] ?? 'system')
  const density = String(values['ui.density'] ?? 'comfortable')
  const font = String(values['ui.font_scale'] ?? 'normal')
  const reduced = values['ui.reduced_motion'] !== false || systemReduced
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    root.setAttribute('data-density', density)
    root.setAttribute('data-font', font)
    root.classList.toggle('reduce-motion', reduced)
  }, [theme, density, font, reduced])
  return {
    theme,
    density,
    font,
    reduced,
    sound: values['ui.sound'] === true,
    ambient: String(values['ui.ambient'] ?? 'off'),
    notifications: values['ui.notifications'] === true,
  }
}
