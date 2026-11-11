import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { ChatPanel } from './ChatPanel'
import { initialChat, type ChatState } from '../chatReducer'
import { t } from '../i18n'
import type { TutorTurn } from '../types'

vi.mock('../voice/useSpeech', () => ({
  useSpeech: () => ({ cancelSpeech: vi.fn(), speak: vi.fn(), support: { tts: false }, muted: true }),
}))
vi.mock('../voice/VoiceBar', () => ({ VoiceBar: () => null }))
vi.mock('./TurnView', () => ({ TurnView: ({ turn }: { turn: TutorTurn }) => <p>{turn.text}</p> }))
const props = { s: t('en'), language: 'en' as const, draftStorageKey: 'synthetic-user-A/session-1' }
beforeEach(() => localStorage.clear())
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

test('failed outgoing question survives remount and restores only on explicit action', () => {
  const send = vi.fn()
  const text = 'Meine Frage: α / 日本語 / SELECT?'
  const view = render(<ChatPanel {...props} chat={initialChat} onSend={send} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: text } })
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(send).toHaveBeenCalledWith(text, 'text')
  view.unmount()
  render(<ChatPanel {...props} chat={{ ...initialChat, error: 'network unavailable' }} onSend={send} />)
  expect(screen.getByText(text)).toBeVisible()
  expect(screen.getByRole('textbox')).toHaveValue('')
  expect(send).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Restore question to editor' }))
  expect(screen.getByRole('textbox')).toHaveValue(text)
  expect(send).toHaveBeenCalledTimes(1)
})

test('successful answer clears pending question while retaining newer unsent notes', async () => {
  const send = vi.fn()
  const view = render(<ChatPanel {...props} chat={initialChat} onSend={send} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'First question' } })
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
  const streaming: ChatState = { ...initialChat, streaming: { text: '', tools: [], rewrites: [] } }
  view.rerender(<ChatPanel {...props} chat={streaming} onSend={send} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Newer unsent research notes' } })
  const turn: TutorTurn = {
    text: 'Complete answer',
    speech: '',
    mode: 'neutral',
    language: 'en',
    persona_on: false,
    diagrams: [],
    citations: [],
    next_question: null,
    path: null,
    ledger_delta: [],
    lab_action: null,
    incident: null,
    session_end: null,
    guard_flags: [],
  }
  const otherTurn: ChatState['items'] = [
    { kind: 'user', id: 'other-question', text: 'Different question from another client' },
    { kind: 'tutor', id: 'other-answer', turn },
  ]
  view.rerender(<ChatPanel {...props} chat={{ ...initialChat, items: otherTurn }} onSend={send} />)
  expect(JSON.parse(localStorage.getItem(props.draftStorageKey)!).pending?.text).toBe('First question')
  view.rerender(
    <ChatPanel
      {...props}
      chat={{ ...initialChat, items: [...otherTurn, { kind: 'user', id: 'sent', text: 'First question' }, { kind: 'tutor', id: 'answer', turn }] }}
      onSend={send}
    />,
  )
  await waitFor(() => expect(JSON.parse(localStorage.getItem(props.draftStorageKey)!).pending).toBeNull())
  expect(screen.getByRole('textbox')).toHaveValue('Newer unsent research notes')
  expect(JSON.parse(localStorage.getItem(props.draftStorageKey)!).draft).toBe('Newer unsent research notes')
})

test('learner/session storage namespaces do not share drafts', () => {
  const view = render(<ChatPanel {...props} chat={initialChat} onSend={vi.fn()} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Private synthetic draft A' } })
  view.unmount()
  render(
    <ChatPanel {...props} draftStorageKey="synthetic-user-B/session-1" chat={initialChat} onSend={vi.fn()} />,
  )
  expect(screen.getByRole('textbox')).toHaveValue('')
  expect(localStorage.getItem(props.draftStorageKey)).toContain('Private synthetic draft A')
})

test('storage failure keeps current text and reports the actual persistence failure', () => {
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  render(<ChatPanel {...props} chat={initialChat} onSend={vi.fn()} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Keep this question' } })
  expect(screen.getByRole('textbox')).toHaveValue('Keep this question')
  expect(screen.getByRole('status')).toHaveTextContent('Browser storage is unavailable')
})

test('a new draft cannot overwrite an unresolved question; explicit append preserves both', () => {
  localStorage.setItem(
    props.draftStorageKey,
    JSON.stringify({ draft: '', pending: { text: 'Failed question A', afterTutorCount: 0 } }),
  )
  const send = vi.fn()
  render(<ChatPanel {...props} chat={initialChat} onSend={send} />)
  fireEvent.change(screen.getByRole('textbox'), { target: { value: 'New notes B' } })
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  expect(JSON.parse(localStorage.getItem(props.draftStorageKey)!).pending.text).toBe('Failed question A')
  fireEvent.click(screen.getByRole('button', { name: 'Append saved question to draft' }))
  expect(screen.getByRole('textbox')).toHaveValue('New notes B\n\nFailed question A')
  expect(send).not.toHaveBeenCalled()
})


test('literal lab shares pending-question recovery and preserves an unsent research draft', () => {
  const send = vi.fn()
  const view = render(<ChatPanel {...props} membershipLab chat={initialChat} onSend={send} />)
  fireEvent.change(screen.getByLabelText(t('en').placeholder), { target: { value: 'Unsent research note' } })
  fireEvent.change(screen.getByLabelText(t('en').membershipOuter), { target: { value: '1' } })
  fireEvent.submit(screen.getByLabelText(t('en').membershipOuter).closest('form')!)
  expect(send).toHaveBeenCalledOnce()
  expect(send.mock.calls[0][0]).toContain('outer value 1 and inner values [1,null]')
  expect(JSON.parse(localStorage.getItem(props.draftStorageKey)!).pending.text).toEqual(send.mock.calls[0][0])
  expect(screen.getByLabelText(t('en').placeholder)).toHaveValue('Unsent research note')
  view.unmount()
  render(<ChatPanel {...props} membershipLab chat={{ ...initialChat, error: 'offline' }} onSend={send} />)
  expect(screen.getByLabelText(t('en').membershipOuter)).toHaveValue('1')
  expect(screen.getByLabelText(t('en').placeholder)).toHaveValue('Unsent research note')
  expect(send).toHaveBeenCalledOnce()
})
