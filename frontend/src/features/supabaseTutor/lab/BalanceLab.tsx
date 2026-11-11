import { useState } from 'react'
import { readDraft, writeDraft } from '../chat/draftStorage'
import type { Strings } from '../i18n'

const defaults = { initial: '100', a: '20', operation: 'subtract', b: '30' }
function restore(key?: string) {
  try {
    const v = JSON.parse(readDraft(key).draft)
    if (
      ['initial', 'a', 'b'].every((k) => typeof v[k] === 'string') &&
      ['subtract', 'set'].includes(v.operation)
    )
      return v as typeof defaults
  } catch {
    /* No saved trial. */
  }
  return defaults
}

export function BalanceLab({
  s,
  language,
  disabled,
  storageKey,
  onRun,
}: {
  s: Strings
  language: 'en' | 'de'
  disabled: boolean
  storageKey?: string
  onRun: (text: string) => void
}) {
  const [v, setValues] = useState(() => restore(storageKey))
  const [invalid, setInvalid] = useState(false)
  const [storageFailed, setStorageFailed] = useState(false)
  function change(key: keyof typeof defaults, value: string) {
    const next = { ...v, [key]: value }
    setValues(next)
    setInvalid(false)
    setStorageFailed(!writeDraft(storageKey, { draft: JSON.stringify(next), pending: null }))
  }
  function run() {
    if (disabled) return
    if (![v.initial, v.a, v.b].every((n) => /^[0-9]{1,7}$/.test(n) && Number(n) <= 1000000)) {
      setInvalid(true)
      return
    }
    const [initial, a, b] = [v.initial, v.a, v.b].map(Number)
    onRun(
      language === 'de'
        ? `Starte einen lokalen Read-Committed-Kontoversuch: Start ${initial}, A subtrahiert ${a}, B ${v.operation === 'set' ? 'setzt' : 'subtrahiert'} ${b}.`
        : `Run a local Read Committed balance trial: start ${initial}, A subtracts ${a}, B ${v.operation === 'set' ? 'sets' : 'subtracts'} ${b}.`,
    )
  }
  const input = (key: 'initial' | 'a' | 'b', label: string) => (
    <label className="block">
      {label}
      <input
        className="block w-full rounded border border-line bg-surface p-2"
        inputMode="numeric"
        maxLength={7}
        value={v[key]}
        disabled={disabled}
        onChange={(e) => change(key, e.target.value)}
      />
    </label>
  )
  return (
    <form
      className="grid gap-2 p-3 text-sm"
      onSubmit={(e) => {
        e.preventDefault()
        run()
      }}
    >
      <p>{s.balanceHint}</p>
      {input('initial', s.balanceInitial)}
      {input('a', s.balanceDebit)}
      <label>
        {s.balanceOperation}
        <select
          className="block w-full rounded border border-line bg-surface p-2"
          value={v.operation}
          disabled={disabled}
          onChange={(e) => change('operation', e.target.value)}
        >
          <option value="subtract">{s.balanceSubtract}</option>
          <option value="set">{s.balanceSet}</option>
        </select>
      </label>
      {input('b', v.operation === 'set' ? s.balanceLiteral : s.balanceAmount)}
      {invalid && <p role="alert">{s.balanceInvalid}</p>}
      {storageFailed && <p role="status">{s.draftNotSaved}</p>}
      <button
        disabled={disabled}
        type="submit"
        className="rounded border border-line p-2 disabled:opacity-40"
      >
        {s.balanceRun}
      </button>
    </form>
  )
}
