import { useState } from 'react'
import type { Strings } from '../i18n'
import { readDraft, writeDraft } from '../chat/draftStorage'

function savedValues(key?: string): { workers: string; minimum: string; first: string } {
  try {
    const value = JSON.parse(readDraft(key).draft)
    if (typeof value.workers === 'string' && typeof value.minimum === 'string' && typeof value.first === 'string') return value
  } catch { /* Keep the saved entry until the learner edits the form. */ }
  return { workers: '2', minimum: '1', first: 'a' }
}

export function IsolationLab({ s, language, disabled, storageKey, descriptionId, onRun }: {
  s: Strings; language: 'en' | 'de'; disabled: boolean; storageKey?: string; descriptionId?: string
  onRun: (text: string) => void
}) {
  const [values, setValues] = useState(() => savedValues(storageKey))
  const [error, setError] = useState(false)
  const [storageFailed, setStorageFailed] = useState(false)
  function change(next: typeof values) {
    setValues(next)
    setError(false)
    setStorageFailed(!writeDraft(storageKey, { draft: JSON.stringify(next), pending: null }))
  }
  function run() {
    if (disabled) return
    const workers = Number(values.workers), minimum = Number(values.minimum)
    if (!/^\d{1,2}$/.test(values.workers) || !/^\d{1,2}$/.test(values.minimum)
      || workers < 2 || workers > 20 || minimum < 0 || minimum > workers || !['a', 'b'].includes(values.first)) {
      setError(true)
      return
    }
    const first = values.first.toUpperCase()
    onRun(language === 'de'
      ? `Vergleiche Transaktionsisolation lokal mit ${workers} aktiven Kräften, mindestens ${minimum}, und Commit-Versuch ${first} zuerst.`
      : `Compare transaction isolation locally for ${workers} active workers, minimum ${minimum}, attempting ${first}'s commit first.`)
  }
  return <form className="space-y-2 p-3" onSubmit={event => { event.preventDefault(); run() }}>
    <p id={descriptionId} className="text-sm">{s.isolationHint}</p>
    <label className="block text-sm">{s.isolationWorkers}
      <input className="block w-full rounded border border-line bg-surface p-2" value={values.workers}
        inputMode="numeric" maxLength={2} disabled={disabled}
        onChange={event => change({ ...values, workers: event.target.value })} />
    </label>
    <label className="block text-sm">{s.isolationMinimum}
      <input className="block w-full rounded border border-line bg-surface p-2" value={values.minimum}
        inputMode="numeric" maxLength={2} disabled={disabled}
        onChange={event => change({ ...values, minimum: event.target.value })} />
    </label>
    <label className="block text-sm">{s.isolationFirst}
      <select className="block w-full rounded border border-line bg-surface p-2" value={values.first}
        disabled={disabled} onChange={event => change({ ...values, first: event.target.value })}>
        <option value="a">{s.isolationFirstA}</option><option value="b">{s.isolationFirstB}</option>
      </select>
    </label>
    {error && <p role="alert">{s.isolationInvalid}</p>}
    {storageFailed && <p role="status">{s.draftNotSaved}</p>}
    <button type="submit" disabled={disabled} className="rounded border border-line p-2 text-sm disabled:opacity-40">{s.isolationRun}</button>
  </form>
}
