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
// CodeMirror measures the DOM through Range client rects, which jsdom does not implement.
const noRects = () =>
  ({ length: 0, item: () => null, [Symbol.iterator]: [][Symbol.iterator] }) as unknown as DOMRectList
if (!Range.prototype.getClientRects) Range.prototype.getClientRects = noRects
if (!Range.prototype.getBoundingClientRect)
  Range.prototype.getBoundingClientRect = () => new DOMRect(0, 0, 0, 0)

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => cleanup())

expect.extend(matchers)
