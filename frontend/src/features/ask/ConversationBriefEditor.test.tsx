import { fireEvent, render, screen } from '@testing-library/react'
import { useState } from 'react'
import { expect, it } from 'vitest'
import { ConversationBriefEditor } from './ConversationBriefEditor'
import { emptyBrief, parseBriefDraft, savedBrief, validBrief } from './conversationBrief'

it('keeps an intentional clear distinct from absent draft and rejects malformed data', () => {
  expect(parseBriefDraft('')).toBeNull()
  expect(parseBriefDraft('{}')).toEqual(emptyBrief())
  expect(() => parseBriefDraft('{bad')).toThrow()
  expect(validBrief({ notes: 'x'.repeat(1501) })).toBe(false)
  expect(validBrief({ verified: true })).toBe(false)
  expect(savedBrief({ conversation_brief: { value: {} } })).toBeNull()
})
it('clears and restores the actual edited notes without submitting', () => {
  function Fixture() {
    const [value, change] = useState({ ...emptyBrief(), task: 'Understand weights' })
    return <ConversationBriefEditor value={value} change={change} disabled={false} invalid={false} />
  }
  render(<Fixture />)
  fireEvent.click(screen.getByText('Keep context for this conversation (optional)'))
  const task = screen.getByLabelText('Current task')
  fireEvent.change(task, { target: { value: 'Compare two models' } })
  fireEvent.click(screen.getByRole('button', { name: 'Clear retained notes' }))
  expect(task).toHaveValue('')
  fireEvent.click(screen.getByRole('button', { name: 'Undo clear' }))
  expect(task).toHaveValue('Compare two models')
})

it('rejects a stale hash instead of prefilling rejected stored notes', async () => {
  const { checkedSavedBrief } = await import('./conversationBrief')
  const value = { ...emptyBrief(), task: 'Original task' }
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value)))
  const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('')
  const envelope = { mode: 'supplied', origin: 'learner_supplied_unverified', value, hash }
  expect(await checkedSavedBrief({ conversation_brief: envelope })).toEqual(value)
  expect(await checkedSavedBrief({ conversation_brief: { ...envelope, value: { ...value, task: 'Changed' } } })).toBeNull()
})
