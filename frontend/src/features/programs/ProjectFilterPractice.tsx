import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'

const points = [
  { id: 'A', tenant: 'blue', topic: 'logs', vector: [2, 1] },
  { id: 'B', tenant: 'red', topic: 'logs', vector: [5, 1] },
  { id: 'C', tenant: 'blue', topic: 'logs', vector: [3, 1] },
  { id: 'D', tenant: 'blue', topic: 'metrics', vector: [4, 1] },
]
const query = [1, 1]

export function ProjectFilterPractice({
  evidence,
  disabled,
  onAppend,
}: {
  evidence: string
  disabled: boolean
  onAppend: (entry: string) => void
}) {
  const [topic, setTopic] = useState('logs')
  const [prediction, setPrediction] = useState('')
  const [checked, setChecked] = useState(false)
  const ranked = points
    .filter((p) => p.tenant === 'blue' && p.topic === topic)
    .map((p) => ({ id: p.id, score: p.vector.reduce((sum, value, i) => sum + value * query[i], 0) }))
    .sort((a, b) => b.score - a.score)
  const observed = ranked.map((row) => row.id).join(', ') || 'none'
  const matches = prediction.toLowerCase().replace(/\s+/g, '') === observed.toLowerCase().replace(/\s+/g, '')
  const entry = [
    'Exact dot-product fixture: query [1, 1], tenant blue, topic ' + topic + '.',
    'My prediction: ' + prediction.trim(),
    'Observed IDs in rank order: ' + observed + '.',
  ].join('\n')
  const fits = [evidence, entry].filter(Boolean).join('\n\n').length <= 24000
  return (
    <Disclosure label="Practice filtered vector retrieval">
      <p>
        This browser fixture runs exact dot-product search. For query [1, 1], add the two coordinates to score
        a point. Keep only points matching both payload conditions, then order them by highest score.
      </p>
      <table>
        <caption>Synthetic points</caption>
        <thead>
          <tr>
            {['ID', 'Tenant', 'Topic', 'Vector'].map((label) => (
              <th scope="col" key={label}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.id}>
              <th scope="row">{p.id}</th>
              <td>{p.tenant}</td>
              <td>{p.topic}</td>
              <td>[{p.vector.join(', ')}]</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>Tenant is fixed to blue.</p>
      <label>
        Topic filter{' '}
        <select
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value)
            setChecked(false)
            setPrediction('')
          }}
        >
          {['logs', 'metrics', 'traces'].map((value) => (
            <option key={value}>{value}</option>
          ))}
        </select>
      </label>
      <label>
        Predicted IDs in rank order (comma-separated, or none)
        <input
          value={prediction}
          maxLength={100}
          onChange={(e) => {
            setPrediction(e.target.value)
            setChecked(false)
          }}
        />
      </label>
      <Button disabled={!prediction.trim()} onClick={() => setChecked(true)}>
        Run filtered search
      </Button>
      {checked && (
        <div>
          <p role="status">
            {matches ? 'Prediction matches.' : 'Compare your prediction with the observed order.'} Observed
            IDs: {observed}.
            {ranked.length > 0 &&
              ' Scores: ' + ranked.map((row) => row.id + ' = ' + row.score).join(', ') + '.'}
          </p>
          <p>
            In your reflection, explain why a high-scoring point can be excluded and who should choose the
            tenant filter.
          </p>
          <Button disabled={disabled || !fits || evidence.includes(entry)} onClick={() => onAppend(entry)}>
            Add run to project evidence
          </Button>
          {!fits && <p>Your evidence is near its limit. Make room before adding this run.</p>}
        </div>
      )}
    </Disclosure>
  )
}
