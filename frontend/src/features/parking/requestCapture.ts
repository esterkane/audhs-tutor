import { validThoughtContext, type ThoughtContext } from './context'

export const CAPTURE_REQUEST = 'audhs:capture-request'
export function requestCapture(context: ThoughtContext, trigger: HTMLElement) {
  if (validThoughtContext(context)) window.dispatchEvent(new CustomEvent(CAPTURE_REQUEST, { detail: { context, trigger } }))
}

/** Open the existing capture dialog without inventing passage provenance. */
export function requestGeneralCapture(trigger: HTMLElement) {
  window.dispatchEvent(new CustomEvent(CAPTURE_REQUEST, { detail: { general: true, trigger } }))
}
