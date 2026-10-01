import { useId, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Textarea } from '../../components/ui/textarea'
import type { Schemas } from '../../lib/api'
import { useQuestionFeedback } from './api'
type Target = Pick<Schemas['FeedbackIn'], 'draft_id' | 'draft_version' | 'question_index' | 'assessment_id'>
const labels: Array<[Schemas['FeedbackIn']['labels'][number], string]> = [
  ['clear', 'Clear and specific'],
  ['useful_application', 'Useful application'],
  ['connects_ideas', 'Connects ideas'],
  ['incorrect', 'Incorrect or unsupported'],
  ['off_topic', 'Off topic'],
  ['too_vague', 'Too vague'],
  ['too_easy', 'Too easy'],
  ['too_hard', 'Too hard'],
  ['other', 'Another reason'],
]
export function QuestionFeedback({ target }: { target: Target }) {
  const id = useId()
  const { save, withdraw } = useQuestionFeedback()
  const [verdict, setVerdict] = useState<'good' | 'bad'>('good')
  const [reason, setReason] = useState<Schemas['FeedbackIn']['labels'][number] | ''>('')
  const [note, setNote] = useState('')
  const [saved, setSaved] = useState<string | null>(null)
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer">Rate this question</summary>
      <p className="text-muted mt-2">
        Tell the app what helps or needs fixing. This does not change your score or mastery.
      </p>
      <label htmlFor={`${id}-verdict`} className="block mt-2">
        Quality
      </label>
      <select
        id={`${id}-verdict`}
        value={verdict}
        onChange={(e) => setVerdict(e.target.value as 'good' | 'bad')}
        className="border border-line rounded p-2"
      >
        <option value="good">Good question</option>
        <option value="bad">Needs improvement</option>
      </select>
      <label htmlFor={`${id}-reason`} className="block mt-2">
        Why?
      </label>
      <select
        id={`${id}-reason`}
        value={reason}
        onChange={(e) => setReason(e.target.value as typeof reason)}
        className="border border-line rounded p-2"
      >
        <option value="">Choose a reason…</option>
        {labels.map(([key, label]) => (
          <option key={key} value={key}>
            {label}
          </option>
        ))}
      </select>
      <label htmlFor={`${id}-note`} className="block mt-2">
        Your explanation (optional)
      </label>
      <Textarea id={`${id}-note`} value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} />
      <Button
        disabled={save.isPending || !reason}
        onClick={() =>
          save.mutate(
            { ...target, verdict, labels: reason ? [reason] : [], note },
            { onSuccess: (r) => setSaved(r.id) },
          )
        }
      >
        Save question feedback
      </Button>
      {saved && (
        <p role="status">
          Feedback saved.{' '}
          <Button
            variant="ghost"
            disabled={withdraw.isPending}
            onClick={() => withdraw.mutate(saved, { onSuccess: () => setSaved(null) })}
          >
            Undo rating
          </Button>
        </p>
      )}
      {(save.error || withdraw.error) && <p role="alert">{(save.error || withdraw.error)?.message}</p>}
    </details>
  )
}
export function FeedbackPreferences() {
  const { query, preference, withdraw } = useQuestionFeedback()
  const options: Array<[Schemas['FeedbackPreference']['key'], string]> = [
    ['questions.applied', 'More concrete application and debugging questions'],
    ['questions.connections', 'More evidence-supported connections across sources'],
    ['questions.step_by_step', 'One focused question at a time'],
  ]
  return (
    <details className="mt-4">
      <summary className="cursor-pointer font-medium">Your feedback and question preferences</summary>
      <p className="text-sm text-muted mt-2">
        Choose how future area drafts should be written. Preferences are changeable; they are not a fixed
        learning style. Ratings alone do not prove learning effectiveness or retrain the model.
      </p>
      <p className="text-sm mt-2">
        Feedback reasons:{' '}
        {Object.entries(query.data?.label_counts ?? {})
          .map(([k, n]) => `${k.replaceAll('_', ' ')} (${n})`)
          .join(' · ') || 'none yet'}
      </p>
      {(query.data?.suggestions ?? []).map((s) => (
        <div key={s.key} className="border border-line rounded p-3 mt-2">
          <p className="text-sm">{s.reason}</p>
          <p className="text-sm mt-1">{s.description}</p>
          <Button
            disabled={preference.isPending}
            onClick={() =>
              preference.mutate({ key: s.key as Schemas['FeedbackPreference']['key'], enabled: true })
            }
          >
            Apply this preference
          </Button>
          <p className="text-xs text-muted">Leave it unchecked to keep your current preferences.</p>
        </div>
      ))}
      {options.map(([key, label]) => (
        <label className="flex items-start gap-2 my-2 text-sm" key={key}>
          <input
            type="checkbox"
            checked={query.data?.preferences[key] ?? false}
            disabled={preference.isPending || !query.data}
            onChange={(e) => preference.mutate({ key, enabled: e.target.checked })}
          />
          {label}
        </label>
      ))}
      {(query.error || preference.error || withdraw.error) && (
        <p role="alert">{(query.error || preference.error || withdraw.error)?.message}</p>
      )}
      <ul className="text-sm grid gap-2">
        {query.data?.feedback
          ?.filter((f) => !f.withdrawn)
          .slice(0, 10)
          .map((f) => (
            <li key={f.id}>
              {f.verdict === 'good' ? 'Good' : 'Needs improvement'}: {f.labels.join(', ')}{' '}
              {f.note && `— ${f.note}`}
              <Button
                variant="ghost"
                size="sm"
                disabled={withdraw.isPending}
                onClick={() => withdraw.mutate(f.id)}
              >
                Withdraw rating
              </Button>
            </li>
          ))}
      </ul>
    </details>
  )
}
