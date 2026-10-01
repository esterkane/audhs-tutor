import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { apiFetch, type Schemas } from '../../lib/api'

type Props = {
  answerId?: string | null
  receipt?: string | null
  error?: string | null
  text: string
  onSaved?: (answerId: string) => void
  linkLabel?: string
}

export function AnswerSaveStatus(props: Props) {
  const [saved, setSaved] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const operation = useRef<AbortController | null>(null)
  const qc = useQueryClient()
  useEffect(() => () => {
    operation.current?.abort()
    operation.current = null
  }, [])
  async function retry() {
    if (!props.receipt || operation.current) return
    const ctl = new AbortController()
    operation.current = ctl
    setBusy(true)
    setError('')
    const timer = setTimeout(() => {
      if (operation.current !== ctl) return
      operation.current = null
      setBusy(false)
      setError('Saving timed out. Your answer remains here; retry saving.')
      ctl.abort()
    }, 15000)
    try {
      const result = await apiFetch<Schemas['AnswerSaveResult']>('/api/answers/recover-save', {
        method: 'POST', body: JSON.stringify({ receipt: props.receipt }), signal: ctl.signal,
      })
      if (operation.current !== ctl || ctl.signal.aborted) return
      setSaved(result.answer_id)
      props.onSaved?.(result.answer_id)
      void qc.invalidateQueries({ queryKey: ['answers'] })
    } catch (cause) {
      if (operation.current === ctl)
        setError(ctl.signal.aborted ? 'Saving timed out. Your answer remains here; retry saving.' : (cause as Error).message)
    } finally {
      clearTimeout(timer)
      if (operation.current === ctl) {
        operation.current = null
        setBusy(false)
      }
    }
  }
  function download() {
    const url = URL.createObjectURL(new Blob([props.text], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'tutor-answer.txt'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const id = props.answerId ?? saved
  if (id) return <p role="status" className="text-sm text-muted">
    Saved to your local answer history. <Link to={`/answers/${encodeURIComponent(id)}`}>{props.linkLabel ?? 'Open saved answer'}</Link>
  </p>
  if (!props.error) return null
  return <div className="text-sm grid gap-2">
    <p role="alert">{error || props.error}</p>
    {props.receipt && <>
      <Button disabled={busy} onClick={() => void retry()}>{busy ? 'Saving…' : 'Retry saving'}</Button>
      <p>Retries only the save, with no new model call. Available for one hour and until the backend restarts. Keep a copy before leaving.</p>
    </>}
    <Button onClick={download}>Save a text copy</Button>
  </div>
}
