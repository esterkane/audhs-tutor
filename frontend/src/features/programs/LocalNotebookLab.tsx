import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, type Schemas } from '../../lib/api'
import { Button } from '../../components/ui/button'

export function LocalNotebookLab({ courseId }: { courseId: string }) {
  const cache = useQueryClient()
  const state = useQuery({
    queryKey: ['notebook-lab'],
    queryFn: () => apiFetch<Schemas['NotebookStatus']>('/api/notebooks/status'),
    refetchInterval: (query) =>
      ['preparing', 'installing', 'starting'].includes(query.state.data?.status ?? '') ? 1000 : false,
  })
  const start = useMutation({
    mutationFn: (install: boolean) =>
      apiFetch<Schemas['NotebookStatus']>('/api/notebooks/start', {
        method: 'POST',
        headers: { 'X-Notebook-Action': 'start' },
        body: JSON.stringify({ course_id: courseId, install }),
      }),
    onSuccess: (result) => cache.setQueryData(['notebook-lab'], result),
  })
  const busy = start.isPending || ['preparing', 'installing', 'starting'].includes(state.data?.status ?? '')
  const mine = state.data?.course_id === courseId
  return (
    <section aria-label="Complete local notebook" className="grid gap-3">
      <h3 className="font-semibold">Complete notebook with datasets and scientific libraries</h3>
      <p>
        Prepare a private working copy and start Jupyter on this Mac. Existing edits are preserved. The
        notebook opens with its datasets alongside it; no upload or terminal command is needed.
      </p>
      <Button disabled={busy} onClick={() => start.mutate(false)}>
        Prepare and start notebook lab
      </Button>
      {state.isError && (
        <p role="alert">
          Cannot reach notebook setup. <Button onClick={() => void state.refetch()}>Retry status</Button>
        </p>
      )}
      {start.isError && <p role="alert">{start.error.message}</p>}
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
          <Button disabled={busy} onClick={() => start.mutate(true)}>
            Install notebook tools and start lab
          </Button>
        </>
      )}
      {mine && state.data?.status === 'ready' && state.data.url && (
        <a className="underline font-semibold" href={state.data.url} target="_blank" rel="noreferrer">
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
