import { useCallback, useEffect } from 'react'
import { useNotebookCommand } from './useNotebookCommand'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { type Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { Button } from '../../components/ui/button'

export function LocalNotebookLab({ courseId }: { courseId: string }) {
  return <NotebookLabPanel key={courseId} courseId={courseId} />
}

function NotebookLabPanel({ courseId }: { courseId: string }) {
  const cache = useQueryClient()
  const onStatus = useCallback(() => {
    // A historical command receipt must never replace another job's live status.
    void cache.invalidateQueries({ queryKey: ['notebook-lab'] })
  }, [cache])
  const command = useNotebookCommand(courseId, onStatus)
  const state = useQuery({
    queryKey: ['notebook-lab'],
    queryFn: ({ signal }) => boundedRead<Schemas['NotebookStatus']>('/api/notebooks/status', signal, 'Notebook setup'),
    retry: false,
    refetchInterval: (query) =>
      !query.state.error && ['preparing', 'installing', 'starting'].includes(query.state.data?.status ?? '') ? 1000 : false,
  })
  const { observe } = command
  useEffect(() => { if (state.data) observe(state.data) }, [state.data, observe])
  const busy = command.busy || !!command.pending || command.blocked || !state.data?.service_id ||
    ['preparing', 'installing', 'starting'].includes(state.data?.status ?? '')
  async function start(install: boolean) {
    if (busy || !state.data?.service_id) return
    await cache.cancelQueries({ queryKey: ['notebook-lab'] })
    command.start(state.data.service_id, install)
  }
  const mine = state.data?.course_id === courseId
  const ownStatus = mine ? state.data : command.receipt
  return (
    <section aria-label="Complete local notebook" className="grid gap-3">
      <h3 className="font-semibold">Complete notebook with datasets and scientific libraries</h3>
      <p>
        Prepare a private working copy and start Jupyter on this computer. Existing edits are preserved. The
        notebook opens with its datasets alongside it; no upload or terminal command is needed.
      </p>
      <Button disabled={busy} onClick={() => void start(false)}>
        Prepare and start notebook lab
      </Button>
      {state.isPending && <p role="status">Checking local notebook setup…</p>}
      {state.isError && (
        <p role="alert">
          Cannot reach notebook setup. <Button onClick={() => void state.refetch()}>Retry status</Button>
        </p>
      )}
      {command.error && <p role="alert">{command.error}</p>}
      {command.receipt && command.receipt.request_id !== state.data?.request_id &&
        <p>Saved setup result: {command.receipt.message}</p>}
      {command.warning && <p role="status">{command.warning}</p>}
      {command.blocked && <Button onClick={command.continueInMemory}>Continue without reload recovery</Button>}
      {command.pending && <div>
        <p role="status">Your setup request is kept. Checking its status does not start another installation.</p>
        <Button aria-disabled={command.busy} onClick={() => { if (!command.busy) command.check() }}>Check setup status</Button>
      </div>}
      {state.data && (
        <p role={state.data.status === 'error' ? 'alert' : 'status'}>
          {state.data.message}
          {busy && !mine ? ' Another notebook is being prepared.' : ''}
        </p>
      )}
      {mine && state.data?.status === 'needs_install' && (
        <>
          <p>
            One-time download: JupyterLab, Python kernel, NumPy, pandas, Matplotlib and scikit-learn in a
            separate local environment. Course-specific extra packages are not installed automatically.
          </p>
          <Button disabled={busy} onClick={() => void start(true)}>
            Install notebook tools and start lab
          </Button>
        </>
      )}
      {ownStatus?.status === 'ready' && ownStatus.url && (
        <a className="underline font-semibold" href={ownStatus.url} target="_blank" rel="noreferrer">
          Open prepared notebook in Jupyter
        </a>
      )}
      <p>
        Read the instructions, then use Shift+Enter to run cells. Jupyter runs native Python with access to
        your local files; inspect downloaded code before running it. Return to this app’s tab to continue
        learning. No cells are executed or course progress recorded by setup.
      </p>
    </section>
  )
}
