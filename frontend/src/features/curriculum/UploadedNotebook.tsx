import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'
import { LocalNotebookLab } from '../programs/LocalNotebookLab'

export function UploadedNotebook({ documentId, addSource, notes = '' }: { documentId: string; addSource?: (text: string) => void; notes?: string }) {
  const [expanded, setExpanded] = useState(false)
  const source = useQuery({
    queryKey: ['notebook-upload', documentId],
    queryFn: ({ signal }) => boundedRead<Schemas['NotebookUploadAvailability']>(
      `/api/notebooks/uploads/${encodeURIComponent(documentId)}`, signal, 'Uploaded notebook',
    ),
    retry: false,
  })
  const edits = useQuery({
    queryKey: ['notebook-upload-edits', documentId],
    queryFn: ({ signal }) => boundedRead<string[]>(
      `/api/notebooks/uploads/${encodeURIComponent(documentId)}/edits`, signal, 'Saved notebook edits',
    ),
    enabled: false,
    retry: false,
    gcTime: 0,
  })
  if (source.isError) return <p role="status">
    Could not check whether this source opens in Jupyter. <Button onClick={() => void source.refetch()}>Retry notebook lookup</Button>
  </p>
  if (!source.data?.available) return null
  return <Disclosure label="Open uploaded notebook locally" onToggle={event => setExpanded(event.currentTarget.open)}>
    {expanded && <LocalNotebookLab courseId={`upload-${documentId}`} uploadId={documentId} />}
    {expanded && addSource && <div>
      <Button disabled={edits.isFetching} onClick={() => void edits.refetch()}>Check saved Jupyter edits</Button>
      {edits.isError && <p role="status">Could not read saved edits. Save the notebook in Jupyter and retry.</p>}
      {edits.isSuccess && !edits.isFetching && (edits.data.length === 0
        ? <p role="status">No new or changed cell source found.</p>
        : edits.data.map((text, i) => {
          const included = ('\n' + notes + '\n').includes('\n' + text + '\n')
          const combined = notes ? notes + '\n\n' + text : text
          const tooLong = combined.length > 120000
          return <div key={i}>
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap">{text}</pre>
            <Button disabled={included || tooLong} onClick={() => addSource(combined)}>
              {included ? 'Already in source notes' : tooLong ? 'Exceeds source note limit' : 'Add cell to source notes'}
            </Button>
          </div>
        }))}
    </div>}
  </Disclosure>
}
