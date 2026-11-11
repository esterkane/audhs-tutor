import { useQuery } from '@tanstack/react-query'
import { boundedRead } from '../../lib/boundedRead'
import type { Schemas } from '../../lib/api'

export function useUploadedPdfPages(uploadId: string, versionId: string) {
  return useQuery({
    queryKey: ['uploaded-pdf-pages', uploadId, versionId],
    queryFn: ({ signal }) => boundedRead<Schemas['PdfPageSources']>(
      `/api/knowledge-material/uploads/${encodeURIComponent(uploadId)}/versions/${encodeURIComponent(versionId)}/pages`,
      signal, 'PDF page text',
    ),
    enabled: !!uploadId && !!versionId,
    staleTime: Infinity,
    retry: false,
  })
}
