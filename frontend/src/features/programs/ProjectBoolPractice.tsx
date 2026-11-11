import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'

const docs = [
  { id: 'A', status: 'active', tag: 'alerts' },
  { id: 'B', status: 'active', tag: 'logs' },
  { id: 'C', status: 'archived', tag: 'alerts' },
]

export function ProjectBoolPractice({
  evidence,
  disabled,
  onAppend,
}: {
  evidence: string
  disabled: boolean
  onAppend: (entry: string) => void
}) {
  const [required, setRequired] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const [checked, setChecked] = useState(false)
  const query = {
    query: {
      bool: {
        filter: { term: { status: 'active' } },
        should: [{ term: { tag: 'alerts' } }],
        ...(required ? { minimum_should_match: 1 } : {}),
      },
    },
  }
  const hits = docs.filter(
    (doc) =>
      doc.status === query.query.bool.filter.term.status &&
      Number(doc.tag === query.query.bool.should[0].term.tag) >= (query.query.bool.minimum_should_match ?? 0),
  )
  const observed = hits.map((doc) => doc.id).join(', ')
  const predicted = [...selected].sort().join(', ') || 'none'
  const setting = required ? '1' : 'omitted'
  const entry =
    'Elasticsearch bool fixture (active filter, alerts should; minimum_should_match ' +
    setting +
    ').\nMy predicted IDs: ' +
    predicted +
    '. Observed IDs: ' +
    observed +
    '.'
  const fits = [evidence, entry].filter(Boolean).join('\n\n').length <= 24000
  return (
    <Disclosure label="Practice Boolean query matching">
      <p>
        Which documents can this query return? Both fields use keyword mappings. This browser fixture checks
        membership only. Result order does not matter.
      </p>
      <table>
        <caption>Synthetic documents</caption>
        <thead>
          <tr>
            <th scope="col">ID</th>
            <th scope="col">status</th>
            <th scope="col">tag</th>
          </tr>
        </thead>
        <tbody>
          {docs.map((doc) => (
            <tr key={doc.id}>
              <th scope="row">{doc.id}</th>
              <td>{doc.status}</td>
              <td>{doc.tag}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <label>
        Minimum should match{' '}
        <select
          value={setting}
          onChange={(e) => {
            setRequired(e.target.value === '1')
            setSelected([])
            setChecked(false)
          }}
        >
          <option value="omitted">Omit the setting</option>
          <option value="1">Require one should clause</option>
        </select>
      </label>
      <pre className="overflow-x-auto whitespace-pre-wrap">{JSON.stringify(query, null, 2)}</pre>
      <fieldset>
        <legend>My predicted matches (leave empty for none)</legend>
        {docs.map((doc) => (
          <label className="mr-4" key={doc.id}>
            <input
              type="checkbox"
              checked={selected.includes(doc.id)}
              onChange={(e) => {
                setSelected(e.target.checked ? [...selected, doc.id] : selected.filter((id) => id !== doc.id))
                setChecked(false)
              }}
            />{' '}
            {doc.id}
          </label>
        ))}
      </fieldset>
      <Button onClick={() => setChecked(true)}>Check matching documents</Button>
      {checked && (
        <div>
          <p role="status">
            {predicted === observed
              ? 'Prediction matches.'
              : 'Compare your prediction with the matching documents.'}{' '}
            Observed IDs: {observed}.
          </p>
          <p>
            {required
              ? 'Both the active filter and the alerts clause must match.'
              : 'Because this bool query contains a filter, minimum_should_match defaults to zero. An active document can match without the alerts tag.'}{' '}
            The archived document fails the filter even though its tag matches.
          </p>
          <p>Try the other setting, then explain in your reflection which document changes and why.</p>
          <Button disabled={disabled || !fits || evidence.includes(entry)} onClick={() => onAppend(entry)}>
            Add query result to project evidence
          </Button>
          {!fits && <p>Make room in project evidence before adding this result.</p>}
          <a href="https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-bool-query">
            Elasticsearch Boolean query reference
          </a>
        </div>
      )}
    </Disclosure>
  )
}
