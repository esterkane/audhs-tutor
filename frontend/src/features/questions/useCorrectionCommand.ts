import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { ApiError, type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

export type CorrectionCommand =
  | { action: 'create'; body: Schemas['CreateCorrectionDraftRequest'] }
  | { action: 'save'; body: Schemas['SaveCorrectionDraft'] }
  | { action: 'publish'; body: Schemas['PublishCorrectionDraft'] }
export type Receipt = Schemas['CorrectionDraftReceipt']
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function validCommand(value: unknown, scope: string, draftId: string | null): value is CorrectionCommand {
  if (!value || typeof value !== 'object') return false
  const command = value as Record<string, unknown>
  const body = command.body as Record<string, unknown> | undefined
  if (!body || typeof body !== 'object' || Array.isArray(body) ||
      typeof body.request_id !== 'string' || !uuid.test(body.request_id)) return false
  if (draftId) {
    if (command.action === 'publish') return Number.isSafeInteger(body.expected_revision) && Number(body.expected_revision) >= 1 &&
      body.reviewed_sources === true && typeof body.preview_token === 'string' && /^ac1\.[0-9a-f]{64}$/.test(body.preview_token) &&
      Object.keys(body).every(key => ['request_id', 'expected_revision', 'preview_token', 'reviewed_sources'].includes(key))
    return command.action === 'save' && Number.isSafeInteger(body.expected_revision) && Number(body.expected_revision) >= 1 &&
      !!body.candidate && typeof body.candidate === 'object' && !Array.isArray(body.candidate) &&
      new TextEncoder().encode(JSON.stringify(body.candidate)).length <= 100000 &&
      (body.rationale === undefined || typeof body.rationale === 'string' && body.rationale.length <= 4000) &&
      Object.keys(body).every(key => ['request_id', 'expected_revision', 'candidate', 'rationale'].includes(key))
  }
  return command.action === 'create' && typeof body.assessment_id === 'string' && !!body.assessment_id &&
    (body.feedback_id == null || typeof body.feedback_id === 'string') &&
    scope === `create:${body.assessment_id}:${body.feedback_id ?? ''}` &&
    Number.isSafeInteger(body.expected_question_revision) && Number(body.expected_question_revision) >= 0 &&
    typeof body.expected_content_version === 'string' && /^ac1\.[0-9a-f]{64}$/.test(body.expected_content_version) &&
    Object.keys(body).every(key => ['request_id', 'assessment_id', 'feedback_id', 'expected_question_revision', 'expected_content_version'].includes(key))
}

export function useCorrectionCommand(scope: string, draftId: string | null,
  onDone: (receipt: Receipt, command: CorrectionCommand) => void) {
  const key = `correction-command:v1:${scope}`
  const [initial] = useState(() => {
    try {
      const raw = sessionStorage.getItem(key)
      if (!raw) return { pending: null, error: '' }
      if (raw.length > 150000) throw new Error('Oversized record')
      const value = JSON.parse(raw) as { scope: string; command: CorrectionCommand }
      const command = value.command
      if (value.scope !== scope || !validCommand(command, scope, draftId)) throw new Error('Invalid record')
      return { pending: command, error: '' }
    } catch {
      return { pending: null, error: 'Retry details could not be read. Keep your work and check saved drafts before leaving.' }
    }
  })
  const [pending, setPending] = useState<CorrectionCommand | null>(initial.pending)
  const current = useRef(initial.pending)
  const [error, setError] = useState(initial.error)
  const [busy, setBusy] = useState(false)
  const active = useRef<AbortController | null>(null)
  const done = useRef(onDone)
  const mounted = useRef(true)
  useLayoutEffect(() => { done.current = onDone }, [onDone])
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])

  async function execute(command: CorrectionCommand, lookup = false) {
    if (active.current || initial.error) return
    const frozen = current.current ?? JSON.parse(JSON.stringify(command)) as CorrectionCommand
    current.current = frozen
    setPending(frozen)
    try { sessionStorage.setItem(key, JSON.stringify({ scope, command: frozen })) }
    catch { setError('Retry details could not be saved. Nothing new was sent. Keep this page open and retry when storage is available.'); return }
    const controller = new AbortController()
    active.current = controller
    setBusy(true)
    setError('')
    try {
      const path = lookup ? `/api/questions/correction-commands/${encodeURIComponent(frozen.body.request_id)}`
        : frozen.action === 'create' ? '/api/questions/correction-drafts'
          : `/api/questions/correction-drafts/${encodeURIComponent(draftId!)}${frozen.action === 'publish' ? '/publish' : ''}`
      const receipt = await boundedRead<Receipt>(path, controller.signal, 'Draft command', lookup ? undefined : {
        method: frozen.action === 'save' ? 'PUT' : 'POST', body: JSON.stringify(frozen.body),
      })
      if (!mounted.current || active.current !== controller) return
      if (!receipt || typeof receipt.draft_id !== 'string' || !receipt.draft_id ||
          !Number.isSafeInteger(receipt.revision) || receipt.revision < 1 || receipt.status !== (frozen.action === 'publish' ? 'published' : 'draft') ||
          (frozen.action !== 'create' && (receipt.draft_id !== draftId || receipt.revision !== frozen.body.expected_revision + 1)) ||
          (frozen.action === 'publish' && (typeof receipt.replacement_id !== 'string' || !receipt.replacement_id))) {
        throw new ApiError(409, 'correction_receipt_mismatch', 'The saved response does not match this draft. Retry details are kept.')
      }
      if (frozen.action === 'create') {
        const created = await boundedRead<Schemas['CorrectionDraftView']>(
          `/api/questions/correction-drafts/${encodeURIComponent(receipt.draft_id)}`, controller.signal, 'Created draft',
        )
        if (!mounted.current || active.current !== controller) return
        if (created.id !== receipt.draft_id || created.assessment_id !== frozen.body.assessment_id)
          throw new ApiError(409, 'correction_receipt_mismatch', 'The created draft does not match this question. Retry details are kept.')
      }
      try { sessionStorage.removeItem(key) }
      catch { setError('The command completed but retry details could not be cleared. Check its result again before starting another command.'); return }
      current.current = null
      setPending(null)
      done.current(receipt, frozen)
    } catch (cause) {
      if (!mounted.current || controller.signal.aborted || active.current !== controller) return
      // These server responses explicitly rejected this command without a write.
      if (!lookup && cause instanceof ApiError && (cause.status === 422 || ['correction_draft_conflict', 'correction_content_conflict',
        'correction_report_conflict', 'question_state_conflict', 'correction_preview_conflict',
        'correction_not_ready', 'correction_kind_unavailable', 'correction_state_unavailable', 'correction_unchanged'].includes(cause.code))) {
        try { sessionStorage.removeItem(key); current.current = null; setPending(null) }
        catch { /* retain exact command if its retry record cannot be cleared */ }
      }
      setError(cause instanceof ApiError ? cause.message : 'The result is uncertain. Check save status or retry the same command. Your work is kept.')
    } finally {
      if (active.current === controller) active.current = null
      if (mounted.current) setBusy(false)
    }
  }
  return { pending, error, busy, blocked: Boolean(initial.error),
    send: (command: CorrectionCommand) => execute(command),
    retry: () => current.current ? execute(current.current) : Promise.resolve(),
    check: () => current.current ? execute(current.current, true) : Promise.resolve(),
  }
}
