import { BalanceLab } from '../lab/BalanceLab'
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { ChatState } from '../chatReducer'
import type { Strings } from '../i18n'
import type { Language } from '../types'
import { type ServerTts, useSpeech } from '../voice/useSpeech'
import { VoiceBar } from '../voice/VoiceBar'
import { readDraft, writeDraft, type RetainedDraft } from './draftStorage'
import { Markdown } from './Markdown'
import { TurnView } from './TurnView'
import { MembershipLab } from '../lab/MembershipLab'
import { IsolationLab } from '../lab/IsolationLab'

export type InputMode = 'text' | 'voice'

export function ChatPanel({
  chat,
  s,
  language,
  onSend,
  serverTts = null,
  draftStorageKey,
  membershipLab = false,
}: {
  chat: ChatState
  s: Strings
  language: Language
  onSend: (text: string, inputMode: InputMode) => void
  serverTts?: ServerTts | null
  draftStorageKey?: string
  membershipLab?: boolean
}) {
  const balanceDialog = useRef<HTMLDialogElement>(null)
  const balanceTitleId = useId()
  const isolationDialog = useRef<HTMLDialogElement>(null)
  const isolationTitleId = useId()
  const isolationHelpId = useId()
  const [retained, setRetained] = useState(() => readDraft(draftStorageKey))
  const retainedRef = useRef(retained)
  const [storageFailed, setStorageFailed] = useState(false)
  const updateDraft = useCallback(
    (change: (previous: RetainedDraft) => RetainedDraft) => {
      const next = change(retainedRef.current)
      retainedRef.current = next
      setStorageFailed(!writeDraft(draftStorageKey, next))
      setRetained(next)
    },
    [draftStorageKey],
  )
  const draft = retained.draft
  const setDraft = (value: string | ((previous: string) => string)) =>
    updateDraft((previous) => ({
      ...previous,
      draft: typeof value === 'function' ? value(previous.draft) : value,
    }))
  const tutorCount = chat.items.filter((item) => item.kind === 'tutor').length
  useEffect(() => {
    if (retained.pending && tutorCount > retained.pending.afterTutorCount)
      updateDraft((previous) => ({ ...previous, pending: null }))
  }, [tutorCount, retained.pending, updateDraft])
  const sendQuestion = (text: string, mode: InputMode) => {
    updateDraft((previous) => ({ ...previous, pending: { text, afterTutorCount: tutorCount } }))
    onSend(text, mode)
  }
  const end = useRef<HTMLDivElement>(null)
  const busy = chat.streaming !== null

  const voice = useSpeech(
    language,
    (transcript) => {
      // While the tutor is still answering, a spoken reply lands in the draft instead of being lost.
      if (busy || retainedRef.current.pending) setDraft((d) => (d ? `${d} ${transcript}` : transcript))
      else sendQuestion(transcript, 'voice')
    },
    serverTts,
  )
  const { speak } = voice

  const wasStreaming = useRef(false)
  useEffect(() => {
    // speak only the `speech` track of a turn that just finished streaming (not on resume)
    if (wasStreaming.current && !chat.streaming) {
      const last = chat.items.at(-1)
      if (last?.kind === 'tutor' && last.turn.speech) void speak(last.turn.speech, last.id)
    }
    wasStreaming.current = chat.streaming !== null
  }, [chat.streaming, chat.items, speak])

  useEffect(() => {
    // Braces matter: newer Chromium returns a Promise from scrollIntoView, and an effect must not return one.
    end.current?.scrollIntoView?.({ block: 'end' })
  }, [chat.items.length, chat.streaming?.text])

  const submit = () => {
    const text = draft.trim()
    if (!text || busy || retainedRef.current.pending) return
    voice.cancelSpeech()
    sendQuestion(text, 'text')
    setDraft('')
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-1 flex-col" aria-label="chat">
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {chat.items.map((item) =>
          item.kind === 'notice' ? (
            <p key={item.id} className="text-center font-mono text-[11px] text-emerald-400">
              {item.text}
            </p>
          ) : item.kind === 'user' ? (
            <div
              key={item.id}
              className="ml-auto max-w-[85%] rounded bg-zinc-800 px-3 py-2 text-sm whitespace-pre-wrap"
            >
              {item.text}
            </div>
          ) : (
            <div key={item.id} className="max-w-[95%]">
              <TurnView
                turn={item.turn}
                s={s}
                onReplay={
                  voice.support.tts && !voice.muted ? (speech) => void speak(speech, item.id) : undefined
                }
              />
            </div>
          ),
        )}
        {chat.streaming && (
          <div className="max-w-[95%]" aria-live="polite">
            {chat.streaming.rewrites.length > 0 && (
              <p className="mb-1 text-[11px] text-amber-400">
                {s.rewritten}: {chat.streaming.rewrites.at(-1)?.join(', ')}
              </p>
            )}
            {chat.streaming.tools.length > 0 && (
              <ul className="mb-2 flex flex-wrap gap-1 text-[11px]">
                {chat.streaming.tools.map((tool, i) => (
                  <li
                    key={i}
                    title={tool.summary}
                    className={`rounded border px-1.5 py-0.5 font-mono ${
                      tool.isError
                        ? 'border-red-700 text-red-300'
                        : tool.done
                          ? 'border-zinc-700 text-zinc-400'
                          : 'border-sky-700 text-sky-300'
                    }`}
                  >
                    {tool.name === 'compare_isolation_lab' ? s.isolationTitle : tool.name === 'same_row_balance_lab' ? s.balanceTitle : tool.name}
                    {typeof tool.input.query === 'string' ? `: ${tool.input.query}` : ''}
                  </li>
                ))}
              </ul>
            )}
            {chat.streaming.text ? (
              <Markdown text={chat.streaming.text} diagramFailed={s.diagramFailed} tableLabel={s.tableRegion} />
            ) : (
              <p className="text-sm text-zinc-400">{s.thinking} …</p>
            )}
          </div>
        )}
        {chat.error && (
          <p role="alert" className="text-sm text-red-400">
            {s.error}: {chat.error}
          </p>
        )}
        <div ref={end} />
      </div>
      {retained.pending && !busy && (
        <section className="border-t border-zinc-800 p-2" aria-label={s.savedQuestion}>
          <p>{s.savedQuestion}</p>
          <p className="whitespace-pre-wrap [overflow-wrap:anywhere]">{retained.pending.text}</p>
          <button
            className="rounded border border-zinc-700 px-2 py-1 text-sm mr-2"
            type="button"
            onClick={() =>
              updateDraft((previous) => ({
                draft:
                  previous.draft && previous.draft !== previous.pending?.text
                    ? previous.draft + '\n\n' + previous.pending?.text
                    : (previous.pending?.text ?? previous.draft),
                pending: null,
              }))
            }
          >
            {draft ? s.appendQuestion : s.restoreQuestion}
          </button>
          <button type="button" onClick={() => updateDraft((previous) => ({ ...previous, pending: null }))}>
            {s.discardQuestion}
          </button>
        </section>
      )}
      {storageFailed && <p role="status">{s.draftNotSaved}</p>}
      <VoiceBar voice={voice} s={s} />
      <form
        className="flex gap-2 border-t border-zinc-800 p-2"
        onSubmit={(e) => {
          e.preventDefault()
          submit()
        }}
      >
        <textarea
          aria-label={s.placeholder}
          value={draft}
          rows={2}
          placeholder={s.placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              submit()
            }
          }}
          className="flex-1 resize-none rounded border border-zinc-700 bg-zinc-900 p-2 text-sm focus:border-sky-600 focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy || !draft.trim() || retained.pending !== null}
          className="self-end rounded bg-sky-700 px-3 py-1.5 text-sm disabled:opacity-40"
        >
          {s.send}
        </button>
      </form>
      {membershipLab && <>
        <button type="button" aria-haspopup="dialog" disabled={busy || retained.pending !== null}
          className="border-t border-line p-3 text-left text-sm disabled:opacity-40"
          onClick={() => {
            isolationDialog.current?.showModal()
            isolationDialog.current?.querySelector<HTMLInputElement>('input')?.focus()
          }}>{s.isolationTitle}</button>
        <dialog ref={isolationDialog} aria-labelledby={isolationTitleId} aria-describedby={isolationHelpId}
          className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-lg border border-line bg-card text-fg p-0 backdrop:bg-fg/30">
          <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line p-3">
            <h2 id={isolationTitleId} className="min-w-0 break-words text-base font-semibold">{s.isolationTitle}</h2>
            <button type="button" className="rounded border border-line p-2 text-sm"
              onClick={() => isolationDialog.current?.close()}>{s.isolationClose}</button>
          </div>
          <IsolationLab s={s} language={language} disabled={busy || retained.pending !== null}
            storageKey={draftStorageKey ? `${draftStorageKey}:isolation` : undefined}
            descriptionId={isolationHelpId}
            onRun={text => {
              if (busy || retainedRef.current.pending) return
              isolationDialog.current?.close()
              voice.cancelSpeech()
              sendQuestion(text, 'text')
            }} />
        </dialog>
      </>}
      {membershipLab && <>
        <button type="button" aria-haspopup="dialog" disabled={busy || retained.pending !== null}
          className="border-t border-line p-3 text-left text-sm disabled:opacity-40"
          onClick={() => { balanceDialog.current?.showModal(); balanceDialog.current?.querySelector('input')?.focus() }}>{s.balanceTitle}</button>
        <dialog ref={balanceDialog} aria-labelledby={balanceTitleId}
          className="m-auto max-h-[90dvh] w-[calc(100%-2rem)] max-w-md overflow-y-auto rounded-lg border border-line bg-card text-fg p-0 backdrop:bg-fg/30">
          <div className="flex flex-wrap items-start justify-between gap-2 border-b border-line p-3">
            <h2 id={balanceTitleId} className="min-w-0 break-words font-semibold">{s.balanceTitle}</h2>
            <button type="button" onClick={() => balanceDialog.current?.close()} className="rounded border border-line p-2">{s.isolationClose}</button>
          </div>
        <BalanceLab s={s} language={language} disabled={busy || retained.pending !== null}
          storageKey={draftStorageKey ? draftStorageKey + ':balance' : undefined}
          onRun={text => {
            if (busy || retainedRef.current.pending) return
            balanceDialog.current?.close()
            voice.cancelSpeech()
            sendQuestion(text, 'text')
          }} />
        </dialog>
      </>}
      {membershipLab && <details className="border-t border-line">
        <summary className="cursor-pointer p-3 text-sm">{s.membershipTitle}</summary>
        <MembershipLab s={s} language={language} disabled={busy || retained.pending !== null}
          storageKey={draftStorageKey ? `${draftStorageKey}:membership` : undefined}
          onCompare={text => {
            if (busy || retainedRef.current.pending) return
            voice.cancelSpeech()
            sendQuestion(text, 'text')
          }} />
      </details>}
    </section>
  )
}
