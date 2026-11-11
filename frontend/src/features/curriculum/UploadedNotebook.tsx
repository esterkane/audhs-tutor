import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'
import { LocalNotebookLab } from '../programs/LocalNotebookLab'

export function UploadedNotebook({ documentId }: { documentId: string }) {
  const [expanded, setExpanded] = useState(false)
  const source = useQuery({
    queryKey: ['notebook-upload', documentId],
    queryFn: ({ signal }) => boundedRead<Schemas['NotebookUploadAvailability']>(
      `/api/notebooks/uploads/${encodeURIComponent(documentId)}`, signal, 'Uploaded notebook',
    ),
    retry: false,
  })
  if (source.isError) return <p role="status">
    Could not check whether this source opens in Jupyter. <Button onClick={() => void source.refetch()}>Retry notebook lookup</Button>
  </p>
  if (!source.data?.available) return null
  return <Disclosure label="Open uploaded notebook locally" onToggle={event => setExpanded(event.currentTarget.open)}>
    {expanded && <LocalNotebookLab courseId={`upload-${documentId}`} uploadId={documentId} />}
  </Disclosure>
}
