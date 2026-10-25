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
  const inspection = useQuery({
    queryKey: ['notebook-inspection', courseId], enabled: false, retry: false,
    queryFn: ({ signal }) => boundedRead<Schemas['NotebookInspection']>(`/api/notebooks/check?course_id=${encodeURIComponent(courseId)}`, signal, 'Notebook requirements'),
  })
  const unavailableStandard = inspection.data?.unavailable_standard_imports ?? []
  const unavailableOther = (inspection.data?.unavailable_imports ?? []).filter(name => !unavailableStandard.includes(name))
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
      <details>
        <summary>Notebook requirements and exercise readiness</summary>
        <p className="text-sm my-2">Check the prepared working copy and package locations in the app’s notebook Python environment. This does not run cells, install packages or assess your work.</p>
        <Button disabled={busy || inspection.isFetching} onClick={() => void inspection.refetch()}>{inspection.isFetching ? 'Checking notebook requirements…' : 'Check notebook requirements'}</Button>
        {inspection.isError && <p role="alert">Could not check notebook requirements. Your files are unchanged; retry when the local app responds.</p>}
        {inspection.data && <div className="grid gap-2 mt-2" aria-label="Notebook requirements result">
          <p role="status">{inspection.data.message}</p>
          {inspection.data.status === 'checked' && <>
            <p>{inspection.data.code_cells} code cells inspected. Package locations do not prove that imports or cells will execute successfully.</p>
            {!!unavailableStandard.length && <p className="text-warn">Standard-library modules unavailable in this Python build or platform: {unavailableStandard.join(', ')}. Review the course’s platform requirements; these are not ordinary pip package gaps.</p>}
            {!!unavailableOther.length && <p className="text-warn">Imports not found in this environment: {unavailableOther.join(', ')}. Review the course requirements before installing extra packages.</p>}
            {!(inspection.data.unavailable_imports ?? []).length && <p>Imported modules were found in standard package locations or local files. This is not a runtime check.</p>}
          </>}
          {!!(inspection.data.possible_exercise_cells ?? []).length && <p>Possible unfinished exercise cells: {(inspection.data.possible_exercise_cells ?? []).join(', ')}. These contain TODO or ellipsis markers; they are not graded. Complete earlier prerequisites before running dependent cells.</p>}
          {!!(inspection.data.install_cells ?? []).length && <p>Installation commands appear in cells {(inspection.data.install_cells ?? []).join(', ')}. None were run by this check.</p>}
          {!!(inspection.data.unparsed_cells ?? []).length && <p>Partial analysis: cells {(inspection.data.unparsed_cells ?? []).join(', ')} contain unsupported syntax, notebook commands or exceed analysis limits.</p>}
          <p className="text-sm text-muted">Cell numbers count all notebook cells from 1. This is the last check; check again after editing. Jupyter readiness and completed course exercises are separate.</p>
        </div>}
      </details>
      <p>
        Read the instructions, then use Shift+Enter to run cells. Jupyter runs native Python with access to
        your local files; inspect downloaded code before running it. Return to this app’s tab to continue
        learning. No cells are executed or course progress recorded by setup.
      </p>
    </section>
  )
}
