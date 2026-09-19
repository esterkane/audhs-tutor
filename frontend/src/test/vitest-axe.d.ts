import 'vitest'
import type { AxeMatchers } from 'vitest-axe/matchers'

/* eslint-disable @typescript-eslint/no-unused-vars, @typescript-eslint/no-empty-object-type */
declare module 'vitest' {
  interface Assertion<T = unknown, R = unknown> extends AxeMatchers {}
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}
