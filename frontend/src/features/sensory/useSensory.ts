import { useEffect, useState } from 'react'
import { usePreferences } from '../preferences/api'
import { useMode } from '../../stores/mode'

/** Shared root contract; OS reduction is a safety ceiling, including live changes.
 * Existing local-profile choices remain authoritative, with legacy fallbacks. */
export function useSensory() {
  const prefs = usePreferences()
  const initialReduced = useMode((s) => s.reducedMotion)
  const [systemReduced, setSystemReduced] = useState(initialReduced)
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setSystemReduced(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])
  const values = (prefs.data?.values ?? {}) as Record<string, unknown>
  const theme = String(values['ui.theme'] ?? 'system')
  const density = String(values['ui.density'] ?? 'comfortable')
  const font = String(values['ui.font_scale'] ?? 'normal')
  const selectedMotion = String(values['ui.motion'] ?? (values['ui.reduced_motion'] === false ? 'low' : 'off'))
  const motion = systemReduced ? 'off' : selectedMotion
  const reduced = motion === 'off'
  const readable = values['ui.readable_font'] === true
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    root.setAttribute('data-density', density)
    root.setAttribute('data-font', readable ? 'readable' : 'default')
    root.setAttribute('data-text-size', font === 'large' ? 'lg' : font === 'xlarge' ? 'xl' : 'md')
    root.setAttribute('data-motion', motion)
    root.setAttribute('data-effects', 'off')
    root.classList.toggle('reduce-motion', reduced)
  }, [theme, density, font, reduced, motion, readable])
  return {
    theme, density, font, reduced, motion,
    sound: values['ui.sound'] === true,
    ambient: String(values['ui.ambient'] ?? 'off'),
    notifications: values['ui.notifications'] === true,
  }
}
