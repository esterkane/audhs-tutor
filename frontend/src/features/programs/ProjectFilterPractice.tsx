import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'

const points = [
  { id: 'A', tenant: 'blue', topic: 'logs', vector: [2, 1] },
  { id: 'B', tenant: 'red', topic: 'logs', vector: [5, 1] },
  { id: 'C', tenant: 'blue', topic: 'logs', vector: [3, 1] },
  { id: 'D', tenant: 'blue', topic: 'metrics', vector: [4, 1] },
]
function rankedPoints(query: number[], topic?: string) {
  return points
    .filter((p) => p.tenant === 'blue' && (topic === undefined || p.topic === topic))
    .map((p) => ({ id: p.id, score: p.vector.reduce((sum, value, i) => sum + value * query[i], 0) }))
    .sort((a, b) => b.score - a.score)
}
type Ranking = ReturnType<typeof rankedPoints>
const ids = (rows: Ranking) => rows.map((row) => row.id).join(', ') || 'none'
const scores = (rows: Ranking) => rows.map((row) => row.id + ' = ' + row.score).join(', ') || 'none'
const agrees = (answer: string, observed: string) =>
  answer.toLowerCase().replace(/\s+/g, '') === observed.toLowerCase().replace(/\s+/g, '')

function CompareConditions({
  topic,
  baselinePrediction,
  evidence,
  disabled,
  onAppend,
}: {
  topic: string
  baselinePrediction: string
  evidence: string
  disabled: boolean
  onAppend: (entry: string) => void
}) {
  const [prediction, setPrediction] = useState('')
  const [transfer, setTransfer] = useState('')
  const [ran, setRan] = useState(false)
  const [tested, setTested] = useState(false)
  const baseline = rankedPoints([1, 1], topic)
  const withoutTopic = rankedPoints([1, 1])
  const newQuery = rankedPoints([-1, 2])
  const entry = [
    'Controlled exact dot-product comparison on the same synthetic points; tenant blue throughout.',
    `Baseline: topic ${topic}, query [1, 1]. My prediction: ${baselinePrediction.trim()}. Observed scores: ${scores(baseline)}.`,
    `Remove only the topic condition. My prediction: ${prediction.trim()}. Observed scores: ${scores(withoutTopic)}.`,
    `New query [-1, 2], still without a topic condition. My prediction: ${transfer.trim()}. Observed scores: ${scores(newQuery)}.`,
  ].join('\n')
  const fits = [evidence, entry].filter(Boolean).join('\n\n').length <= 24000
  return (
    <Disclosure label="Change one condition">
      <p>Keep the same points, blue tenant and query [1, 1]. Remove only the topic condition.</p>
      <label>
        Predicted order without the topic condition
        <input
          value={prediction}
          maxLength={100}
          onChange={(e) => {
            setPrediction(e.target.value)
            setRan(false)
            setTested(false)
            setTransfer('')
          }}
        />
      </label>
      <Button disabled={!prediction.trim()} onClick={() => setRan(true)}>
        Compare searches
      </Button>
      {ran && (
        <>
          <p role="status">
            {agrees(prediction, ids(withoutTopic))
              ? 'Prediction matches.'
              : 'Compare your prediction with the ranked points.'}{' '}
            With topic {topic}: {scores(baseline)}. Without a topic condition: {scores(withoutTopic)}.
          </p>
          <p>
            The scores of previously eligible points stay the same. Removing the topic condition admits other
            topics within blue.
          </p>
          <p>Now change only the query to [-1, 2]. For each eligible point [x, y], calculate −x + 2y.</p>
          <label>
            Predicted order with the new query
            <input
              value={transfer}
              maxLength={100}
              onChange={(e) => {
                setTransfer(e.target.value)
                setTested(false)
              }}
            />
          </label>
          <Button disabled={!transfer.trim()} onClick={() => setTested(true)}>
            Check new query
          </Button>
          {tested && (
            <>
              <p role="status">
                {agrees(transfer, ids(newQuery))
                  ? 'Prediction matches.'
                  : 'Compare your prediction with the new scores.'}{' '}
                New query scores: {scores(newQuery)}. The blue tenant filter still applies.
              </p>
              <Button
                disabled={disabled || !fits || evidence.includes(entry)}
                onClick={() => onAppend(entry)}
              >
                Add comparison to project evidence
              </Button>
              {!fits && <p>Your evidence is near its limit. Make room before adding this comparison.</p>}
            </>
          )}
        </>
      )}
    </Disclosure>
  )
}

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
  const ranked = rankedPoints([1, 1], topic)
  const observed = ids(ranked)
  const matches = agrees(prediction, observed)
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
          <CompareConditions
            topic={topic}
            baselinePrediction={prediction}
            evidence={evidence}
            disabled={disabled}
            onAppend={onAppend}
          />
        </div>
      )}
    </Disclosure>
  )
}
