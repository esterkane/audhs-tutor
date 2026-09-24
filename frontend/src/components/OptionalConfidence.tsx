import { Choice } from './ui/choice'
import { Button } from './ui/button'

export function OptionalConfidence({
  value,
  onChange,
}: {
  value: number | null
  onChange: (n: number | null) => void
}) {
  return (
    <details className="mt-2 text-sm">
      <summary className="cursor-pointer">Confidence (optional)</summary>
      <Choice<number>
        label="How sure are you? (1 = guessing, 5 = certain)"
        options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
        value={value}
        onChange={onChange}
        columns={5}
      />
      {value != null && (
        <Button variant="ghost" onClick={() => onChange(null)}>
          Skip confidence
        </Button>
      )}
    </details>
  )
}
