import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError, type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'

type Status = Schemas['NotebookStatus']
type Command = { request_id: string; service_id: string; course_id: string; install: boolean }
const uuid = /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i
const terminal = new Set(['ready', 'needs_install', 'error'])
function read(key: string, course: string) {
  try {
    const raw = sessionStorage.getItem(key)
    if (!raw) return { pending: null, warning: '', blocked: false }
    if (raw.length > 1000) throw new Error('Invalid record')
    const value = JSON.parse(raw) as Command
    if (!value || !uuid.test(value.request_id) || !uuid.test(value.service_id) ||
        value.course_id !== course || typeof value.install !== 'boolean' ||
        Object.keys(value).some(k => !['request_id', 'service_id', 'course_id', 'install'].includes(k))) throw new Error('Invalid record')
    return { pending: value, warning: '', blocked: false }
  } catch {
    return { pending: null, warning: 'Setup recovery details could not be read. Keep this page open. You can explicitly continue without reload recovery, but an earlier setup may still be running.', blocked: true }
  }
}

/** One immutable setup intent per course/tab. Never automatically resend a POST. */
export function useNotebookCommand(courseId: string, onStatus: (value: Status) => void) {
  const key = `audhs.notebook-command.v1:${courseId}`
  const [stored, setStored] = useState(() => read(key, courseId))
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<Status | null>(null)
  const [busy, setBusy] = useState(false)
  const memoryOnly = useRef(false)
  const rejected = useRef<string | null>(null)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort(); active.current = null } }, [])

  const complete = useCallback((command: Command, result: Status, publish = true) => {
    if (result.request_id !== command.request_id || result.service_id !== command.service_id || result.course_id !== command.course_id)
      throw new Error('Setup status does not match the saved request. Your request is kept.')
    setReceipt(result)
    if (publish) onStatus(result)
    if (!terminal.has(result.status)) return
    try {
      if (!memoryOnly.current) sessionStorage.removeItem(key)
      setStored(s => ({ ...s, pending: null }))
    } catch {
      setStored(s => ({ ...s, blocked: true, warning: 'Setup finished, but its recovery record could not be cleared. Check again before starting another setup.' }))
    }
  }, [key, onStatus])

  async function execute(command: Command, send: boolean) {
    if (!mounted.current || active.current) return
    const controller = new AbortController()
    active.current = controller
    setBusy(true); setError('')
    try {
      const result = await boundedRead<Status>(send ? '/api/notebooks/start' :
        `/api/notebooks/requests/${command.request_id}?service_id=${command.service_id}`,
      controller.signal, 'Notebook setup acknowledgement', send ? {
        method: 'POST', headers: { 'X-Notebook-Action': 'start' }, body: JSON.stringify(command),
      } : undefined)
      if (active.current === controller) complete(command, result)
    } catch (cause) {
      if (active.current !== controller) return
      // These responses prove THIS new command was not accepted. Never infer that from a timeout.
      if (send && cause instanceof ApiError && ['notebook_busy', 'notebook_receipts_full'].includes(cause.code)) {
        rejected.current = command.request_id
        try {
          if (!memoryOnly.current) sessionStorage.removeItem(key)
          setStored(s => ({ ...s, pending: null }))
        } catch {
          setStored(s => ({ ...s, blocked: true, warning: 'Setup was not accepted, but its recovery record could not be cleared. Continue without reload recovery to release this request.' }))
        }
        setError(cause.message)
      } else setError('Setup acknowledgement is unavailable. It may still be running. Check setup status; this does not start or install anything again.')
    } finally {
      if (active.current === controller) { active.current = null; setBusy(false) }
    }
  }

  function start(serviceId: string, install: boolean) {
    if (!mounted.current || active.current || stored.pending || stored.blocked || !uuid.test(serviceId)) return
    const command = { request_id: crypto.randomUUID(), service_id: serviceId, course_id: courseId, install }
    try {
      if (!memoryOnly.current) sessionStorage.setItem(key, JSON.stringify(command))
    } catch {
      setStored(s => ({ ...s, blocked: true, warning: 'Setup was not sent because recovery details could not be saved. You can explicitly continue without reload recovery.' }))
      return
    }
    rejected.current = null
    setReceipt(null)
    setStored(s => ({ ...s, pending: command }))
    void execute(command, true)
  }
  const observe = useCallback((status: Status) => {
    const pending = stored.pending
    if (pending && !active.current && status.request_id === pending.request_id &&
        status.service_id === pending.service_id && status.course_id === pending.course_id && terminal.has(status.status)) {
      complete(pending, status, false)
    }
  }, [stored.pending, complete])
  return { ...stored, receipt, error, busy, start, observe,
    check: () => { if (stored.pending) void execute(stored.pending, false) },
    continueInMemory: () => {
      memoryOnly.current = true
      setStored(s => ({ ...s, blocked: false, warning: 'Recovery is kept only while this page stays open. Reload may lose this setup request.' }))
      if (stored.pending && rejected.current === stored.pending.request_id) setStored(s => ({ ...s, pending: null }))
      else if (stored.pending && receipt && terminal.has(receipt.status)) complete(stored.pending, receipt, false)
    },
  }
}
