import * as matchers from 'vitest-axe/matchers'
import { expect } from 'vitest'
import '@testing-library/jest-dom/vitest'

// jsdom lacks these; Radix Dialog and Zustand's matchMedia probe need them.
if (!window.matchMedia) {
  window.matchMedia = (q: string) => ({
    matches: false,
    media: q,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent: () => false,
  })
}
class RO {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver = RO
Element.prototype.scrollIntoView = () => {}
Element.prototype.hasPointerCapture = () => false
Element.prototype.releasePointerCapture = () => {}

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())

expect.extend(matchers)
