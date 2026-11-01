import { useState } from 'react'
import type { Strings } from '../i18n'
import { readDraft, writeDraft } from '../chat/draftStorage'

function savedValues(key?: string): { outer: string; inner: string } {
  try {
    const value = JSON.parse(readDraft(key).draft)
    if (typeof value.outer === 'string' && typeof value.inner === 'string') return value
  } catch { /* Preserve the stored entry until the learner edits the values. */ }
  return { outer: '2', inner: '[1, null]' }
}
function valid(value: unknown) {
  return value === null || typeof value === 'number' && Number.isInteger(value) && Math.abs(value) <= 1000000
}

export function MembershipLab({ s, language, disabled, storageKey, onCompare }: {
  s: Strings; language: 'en' | 'de'; disabled: boolean; storageKey?: string
  onCompare: (text: string) => void
}) {
  const [values, setValues] = useState(() => savedValues(storageKey))
  const [error, setError] = useState(false)
  const [storageFailed, setStorageFailed] = useState(false)
  function change(next: typeof values) {
    setValues(next)
    setError(false)
    setStorageFailed(!writeDraft(storageKey, { draft: JSON.stringify(next), pending: null }))
  }
  function compare() {
    if (disabled) return
    try {
      const outer: unknown = JSON.parse(values.outer), inner: unknown = JSON.parse(values.inner)
      if (!valid(outer) || !Array.isArray(inner) || inner.length > 20 || !inner.every(valid)) throw new Error('values')
      const left = JSON.stringify(outer), right = JSON.stringify(inner)
      onCompare(language === 'de'
        ? `Führe einen lokalen Vergleich von NOT IN und korreliertem NOT EXISTS (inner = outer) für den äußeren Wert ${left} und die inneren Werte ${right} aus.`
        : `Run a local comparison of NOT IN and correlated NOT EXISTS (inner = outer) for outer value ${left} and inner values ${right}.`)
    } catch { setError(true) }
  }
  return <form className="space-y-2 p-3" onSubmit={event => { event.preventDefault(); compare() }}>
    <p className="text-sm">{s.membershipHint}</p>
    <label className="block text-sm">{s.membershipOuter}
      <input className="block w-full rounded border border-line bg-surface p-2" value={values.outer}
        maxLength={60} disabled={disabled} onChange={event => change({ ...values, outer: event.target.value })} />
    </label>
    <label className="block text-sm">{s.membershipInner}
      <input className="block w-full rounded border border-line bg-surface p-2" value={values.inner}
        maxLength={400} disabled={disabled} onChange={event => change({ ...values, inner: event.target.value })} />
    </label>
    {error && <p role="alert">{s.membershipInvalid}</p>}
    {storageFailed && <p role="status">{s.draftNotSaved}</p>}
    <button type="submit" disabled={disabled} className="rounded border border-line p-2 text-sm disabled:opacity-40">{s.membershipRun}</button>
  </form>
}
