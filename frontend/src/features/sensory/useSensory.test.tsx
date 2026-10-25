import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { useSensory } from './useSensory'
const data = vi.hoisted(() => ({ values: {} as Record<string, unknown> }))
vi.mock('../preferences/api', () => ({ usePreferences: () => ({ data }) }))
afterEach(() => { cleanup(); vi.unstubAllGlobals(); data.values = {} })
it('retains legacy large text and motion choices, and responds to live OS reduction', () => {
  const media = new EventTarget() as EventTarget & { matches: boolean }
  media.matches = false
  vi.stubGlobal('matchMedia', () => media)
  data.values = { 'ui.font_scale': 'large', 'ui.reduced_motion': false }
  const view = renderHook(useSensory)
  expect(document.documentElement.dataset.textSize).toBe('lg')
  expect(document.documentElement.dataset.motion).toBe('low')
  act(() => { media.matches = true; media.dispatchEvent(new Event('change')) })
  expect(view.result.current.reduced).toBe(true)
  expect(document.documentElement.dataset.motion).toBe('off')
  act(() => { media.matches = false; media.dispatchEvent(new Event('change')) })
  expect(document.documentElement.dataset.motion).toBe('low')
})
it('supports extra large system-font reading and never enables uninstalled effects', () => {
  vi.stubGlobal('matchMedia', () => Object.assign(new EventTarget(), { matches: false }))
  data.values = { 'ui.font_scale': 'xlarge', 'ui.readable_font': true, 'ui.motion': 'full' }
  renderHook(useSensory)
  expect(document.documentElement.dataset.textSize).toBe('xl')
  expect(document.documentElement.dataset.font).toBe('readable')
  expect(document.documentElement.dataset.effects).toBe('off')
})
