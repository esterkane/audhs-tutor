import RelationshipGraph from './RelationshipGraph'
import type { FitScope } from './leakage'
export default function LeakageGraph({ scope, mean }: { scope: FitScope; mean: number }) {
  const pairs = scope === 'train' ? [[0, 2], [0, 3], [2, 3], [1, 3]] : [[0, 2], [0, 3], [1, 2], [2, 3], [1, 3]]
  return <RelationshipGraph graph={{
    title: 'Preprocessing information flow', directed: true,
    textEquivalent: `Arrows show which values a step uses. Training values go to fitting and transformation. The fitted mean goes to transformation. Held-out values go to transformation${scope === 'all' ? ' and also to fitting: that extra connection leaks test information' : ' only'}.`,
    nodes: [
      { id: '0', label: 'Training values', explanation: 'These values are used to learn the preprocessing parameter. Here they are fixed at 2 and 4, so their mean is 3.' },
      { id: '1', label: 'Held-out values', explanation: 'These values stand in for new data. Transform them using a parameter learned from training; do not use them to fit that parameter.' },
      { id: '2', label: `Fit mean = ${mean}`, explanation: scope === 'train' ? `The mean is ${mean}, calculated from training values only. Moving the held-out slider cannot change it.` : `The mean is ${mean}, calculated using both sets. Moving the held-out slider changes a learned parameter: this is leakage, even without outcome labels.` },
      { id: '3', label: 'Apply the same mean', explanation: `Subtract the saved mean (${mean}) from every value in each set. This transformation does not fit a new mean. The held-out results are listed below the diagram.` },
    ],
    edges: pairs.map(([a, b]) => ({ id: `${a}-${b}`, source: String(a), target: String(b) })),
  }} />
}
