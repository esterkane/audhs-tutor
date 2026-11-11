import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { boundedRead } from '../../lib/boundedRead'

import type { components } from '../../lib/api-types'

export type PredictionBinding = { draft_id: string; learning_object_version: number; question_id: string }
type Receipt = components['schemas']['PredictionReceipt']

export function SavePredictionForRecall({
  binding,
  prediction,
}: {
  binding: PredictionBinding
  prediction: string
}) {
  const cache = useQueryClient()
  const key = ['reading-prediction-enrollment', binding]
  const params = new URLSearchParams({
    ...binding,
    learning_object_version: String(binding.learning_object_version),
  })
  const enrollment = useQuery({
    queryKey: key,
    retry: false,
    queryFn: ({ signal }) =>
      boundedRead<Receipt | null>(
        `/api/reading-predictions/enrollment?${params}`,
        signal,
        'Recall enrollment',
      ),
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  async function save() {
    setSaving(true)
    setError('')
    try {
      const receipt = await boundedRead<Receipt>(
        '/api/reading-predictions',
        new AbortController().signal,
        'Saving prediction',
        {
          method: 'POST',
          body: JSON.stringify({ ...binding, prediction }),
        },
      )
      cache.setQueryData(key, receipt)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not confirm the save.')
      await enrollment.refetch()
    } finally {
      setSaving(false)
    }
  }
  if (enrollment.data)
    return (
      <p role="status">
        Saved for later recall. Open{' '}
        <a href="/review?practice=passage" className="underline">
          Passage recall
        </a>{' '}
        after {new Date(enrollment.data.due_at).toLocaleString()}.
      </p>
    )
  if (Array.from(prediction).length > 4000)
    return (
      <p>
        Your original prediction is saved in this browser. Later recall supports predictions up to 4,000
        characters.
      </p>
    )
  return (
    <div className="space-y-2">
      <p>
        To revisit this question after a day, save the original prediction with your learner profile. Your
        comparison stays in this browser.
      </p>
      {enrollment.isError ? (
        <Button onClick={() => void enrollment.refetch()}>Retry recall lookup</Button>
      ) : (
        <Button disabled={saving || enrollment.isPending} onClick={() => void save()}>
          {saving ? 'Saving prediction…' : 'Save prediction for later recall'}
        </Button>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
