import { useState } from 'react'
import { Button } from '../../components/ui/button'

type Row = { label: string; before: string; after: string }
const initial = (): Row[] => [
  { label: 'A', before: '', after: '' },
  { label: 'B', before: '', after: '' },
]
function restore(key: string): { rows: Row[]; warning: string } {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return { rows: initial(), warning: '' }
    const parsed = JSON.parse(raw)
    if (
      parsed.version !== 1 ||
      !Array.isArray(parsed.rows) ||
      parsed.rows.length < 2 ||
      parsed.rows.length > 8 ||
      !parsed.rows.every(
        (row: Row) =>
          row &&
          typeof row.label === 'string' &&
          row.label.length <= 80 &&
          typeof row.before === 'string' &&
          row.before.length <= 32 &&
          typeof row.after === 'string' &&
          row.after.length <= 32,
      )
    )
      throw new Error('Invalid draft')
    return { rows: parsed.rows, warning: '' }
  } catch {
    return { rows: initial(), warning: 'Saved counts could not be loaded. Enter counts to begin.' }
  }
}
function valid(rows: Row[]): boolean {
  const labels = rows.map((row) => row.label.trim())
  return (
    labels.every((label) => label.length > 0 && label.length <= 80) &&
    new Set(labels).size === rows.length &&
    rows.every(
      (row) =>
        /^\d+$/.test(row.before) &&
        /^\d+$/.test(row.after) &&
        Number(row.before) <= 1e9 &&
        Number(row.after) <= Number(row.before),
    )
  )
}
function fraction(numerator: number, denominator: number): string {
  return denominator === 0
    ? 'Not defined (zero total)'
    : `${numerator}/${denominator} = ${((100 * numerator) / denominator).toFixed(2)}%`
}
export function GroupCounts({ storageKey }: { storageKey: string }) {
  return <Counts key={storageKey} storageKey={storageKey} />
}
function Counts({ storageKey }: { storageKey: string }) {
  const [saved] = useState(() => restore(storageKey))
  const [rows, setRows] = useState(saved.rows)
  const [warning, setWarning] = useState(saved.warning)
  const [compared, setCompared] = useState<Row[] | null>(null)
  const [edited, setEdited] = useState(false)
  const [error, setError] = useState('')
  function change(next: Row[]) {
    setRows(next)
    if (compared) setEdited(true)
    setCompared(null)
    setError('')
    try {
      localStorage.setItem(storageKey, JSON.stringify({ version: 1, rows: next }))
      setWarning('')
    } catch {
      setWarning(
        'Counts could not be saved in this browser. Your current entries remain available in this session.',
      )
    }
  }
  const beforeTotal = compared?.reduce((sum, row) => sum + Number(row.before), 0) ?? 0
  const afterTotal = compared?.reduce((sum, row) => sum + Number(row.after), 0) ?? 0
  return (
    <section aria-label="Compare group counts" className="min-w-0 space-y-3">
      <p>
        Enter your own before and after counts. These are user-entered counts, not verified dataset results.
        No code is executed. Counts alone cannot establish fairness.
      </p>
      <p className="text-sm text-muted">
        Use nonoverlapping groups counted in the same unit before and after, with unchanged group membership.
        This comparison assumes rows were removed, not added or reassigned. Representation is the share within
        the groups entered here, not necessarily the entire dataset. Percentages are rounded to two decimal
        places. Counts are not automatically sent to the tutor.
      </p>
      {!warning && (
        <p className="text-sm text-muted">
          Changes are saved in this browser for this session and step, not in the database.
        </p>
      )}
      {rows.map((row, index) => (
        <fieldset key={index} className="min-w-0 border border-line rounded p-2">
          <legend>Group {index + 1}</legend>
          <div className="flex flex-wrap gap-2">
            {(['label', 'before', 'after'] as const).map((field) => (
              <label key={field} className="min-w-0 flex-1">
                {field === 'label' ? 'Group name' : field === 'before' ? 'Before count' : 'After count'}
                <input
                  className="block w-full min-w-0 border border-line rounded px-2 py-1"
                  aria-label={field === 'label' ? `Group name ${index + 1}` : `Group ${index + 1} ${field} count`}
                  type="text"
                  inputMode={field === 'label' ? 'text' : 'numeric'}
                  maxLength={field === 'label' ? 80 : 32}
                  value={row[field]}
                  onChange={(event) =>
                    change(
                      rows.map((item, i) => (i === index ? { ...item, [field]: event.target.value } : item)),
                    )
                  }
                />
              </label>
            ))}
          </div>
          <Button disabled={rows.length <= 2} onClick={() => change(rows.filter((_, i) => i !== index))}>
            Remove group {index + 1}
          </Button>
        </fieldset>
      ))}
      <div className="flex flex-wrap gap-2">
        <Button
          disabled={rows.length >= 8}
          onClick={() => change([...rows, { label: '', before: '', after: '' }])}
        >
          Add group
        </Button>
        <Button
          variant="primary"
          onClick={() => {
            if (!valid(rows)) {
              setError(
                'Use unique nonempty group names and whole-number counts from 0 to 1,000,000,000. After cannot exceed before.',
              )
              return
            }
            setCompared(rows.map((row) => ({ ...row })))
            setEdited(false)
            setError('')
          }}
        >
          Compare counts
        </Button>
      </div>
      {warning && <p role="status">{warning}</p>}
      {error && <p role="alert">{error}</p>}
      {edited && !compared && (
        <p role="status">Counts changed. Compare counts again to update the results.</p>
      )}
      {compared && (
        <div
          className="max-w-full overflow-x-auto"
          tabIndex={0}
          role="region"
          aria-label="Group comparison results"
        >
          <table className="text-sm">
            <caption>User-entered group comparison — not a fairness assessment</caption>
            <thead>
              <tr>
                {[
                  'Group',
                  'Before',
                  'After',
                  'Removed',
                  'Retention',
                  'Removal',
                  'Representation before',
                  'Representation after',
                  'Change in representation',
                ].map((title) => (
                  <th scope="col" key={title} className="p-2">
                    {title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {compared.map((row) => {
                const before = Number(row.before),
                  after = Number(row.after)
                return (
                  <tr key={row.label.trim()}>
                    <th scope="row" className="p-2">
                      {row.label}
                    </th>
                    <td>{before}</td>
                    <td>{after}</td>
                    <td>{before - after}</td>
                    <td>{fraction(after, before)}</td>
                    <td>{fraction(before - after, before)}</td>
                    <td>{fraction(before, beforeTotal)}</td>
                    <td>{fraction(after, afterTotal)}</td>
                    <td>
                      {beforeTotal === 0 || afterTotal === 0
                        ? 'Not defined (zero total)'
                        : `${(100 * (after / afterTotal - before / beforeTotal)).toFixed(2)} percentage points`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
