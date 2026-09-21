/** Per-viewer choice between CodeMirror and the plain <textarea> (browser storage only). */
export const PLAIN_EDITOR_KEY = 'code-editor:plain'

export function readPlainPreference(): boolean {
  try {
    return localStorage.getItem(PLAIN_EDITOR_KEY) === '1'
  } catch {
    return false
  }
}

export function writePlainPreference(plain: boolean) {
  try {
    if (plain) localStorage.setItem(PLAIN_EDITOR_KEY, '1')
    else localStorage.removeItem(PLAIN_EDITOR_KEY)
  } catch {
    /* per-viewer convenience only */
  }
}
