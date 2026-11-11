import { useQuery } from '@tanstack/react-query'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'
import { Disclosure } from '../../components/ui/disclosure'

export function CorrectionComparison({
  sessionId,
  itemId,
  version,
}: {
  sessionId: string
  itemId: string
  version: string
}) {
  const correction = useQuery({
    queryKey: ['review-correction', sessionId, itemId, version],
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Schemas['CorrectionComparison'] | null>(
        `/api/review/items/${encodeURIComponent(itemId)}/correction?${new URLSearchParams({ session_id: sessionId, content_version: version })}`,
        signal,
        'Previous correction',
      ),
  })
  if (!correction.data) return null
  return (
    <Disclosure label="Compare with your earlier correction">
      <p>Your earlier answer: {correction.data.earlier}</p>
      <p>Your corrected answer after feedback: {correction.data.corrected}</p>
      <p>Rate how recall went today using your own judgment.</p>
    </Disclosure>
  )
}
