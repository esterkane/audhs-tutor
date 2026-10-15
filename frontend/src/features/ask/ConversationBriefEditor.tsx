import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { briefFields, emptyBrief, type Brief } from './conversationBrief'

export function ConversationBriefEditor({ value, change, disabled, invalid }: {
  value: Brief; change: (value: Brief) => void; disabled: boolean; invalid: boolean
}) {
  const [undo, setUndo] = useState<Brief | null>(null)
  return <Disclosure label="Keep context for this conversation (optional)" className="my-3">
    <p className="text-sm text-muted mb-3">These are your notes, not checked facts. They stay with this branch until you edit or clear them. Changes apply to your next reply; saved answers keep their original context.</p>
    {invalid && <p role="alert">Saved notes could not be restored. Clear them before sending; no replacement was invented.</p>}
    <fieldset disabled={disabled} className="space-y-3">
      {briefFields.map(([key, label, limit]) => <div key={key} className="block text-sm">
        <label htmlFor={`ask-brief-${key}`} className="font-medium">{label}</label>
        <textarea id={`ask-brief-${key}`} rows={2} maxLength={limit} value={value[key]}
          className="mt-1 w-full rounded border border-line bg-card p-3"
          onChange={event => { setUndo(null); change({ ...value, [key]: event.target.value }) }} />
      </div>)}
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={() => { setUndo(value); change(emptyBrief()) }}>Clear retained notes</Button>
        {undo && <Button type="button" onClick={() => { change(undo); setUndo(null) }}>Undo clear</Button>}
      </div>
    </fieldset>
    <p className="text-sm text-muted mt-2">Clearing notes does not delete earlier questions or answers. Start a new topic to leave the conversation behind.</p>
  </Disclosure>
}
