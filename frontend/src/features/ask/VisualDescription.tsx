import { Disclosure } from '../../components/ui/disclosure'
import type { VisualEdits } from './visualEditing'

type Description = Pick<VisualEdits, 'directed' | 'nodes' | 'edges' | 'text_equivalent'>

export function VisualDescription({ value }: { value: Description }) {
  const labels = new Map(value.nodes.map((node) => [node.id, node.label]))
  return (
    <>
      <p>{value.text_equivalent}</p>
      <Disclosure label="Read all concepts and relationships">
        <ul aria-label="Concepts" className="list-disc pl-5 space-y-2">
          {value.nodes.map((node) => (
            <li key={node.id}>
              <strong>{node.label}:</strong> {node.explanation}
            </li>
          ))}
        </ul>
        {value.edges.length > 0 && (
          <ol aria-label="Numbered diagram connections" className="list-decimal pl-5 space-y-2 mt-3">
            {value.edges.map((edge) => (
              <li key={edge.id}>
                {value.directed ? 'From ' : 'Between '}
                {labels.get(edge.source)}
                {value.directed ? ' to ' : ' and '}
                {labels.get(edge.target)}: {edge.label}
              </li>
            ))}
          </ol>
        )}
      </Disclosure>
    </>
  )
}
