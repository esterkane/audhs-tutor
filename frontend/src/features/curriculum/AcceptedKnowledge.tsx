import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAcceptedKnowledge } from './acceptedKnowledgeApi'
import { Card, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { Markdown } from '../../components/Markdown'
import { LessonReader } from '../tutor/LessonReader'
import { SourceViewer } from './SourceViewer'
import { useState } from 'react'


export function AcceptedKnowledge({ reading, onCheck, active = true }: { reading:ReturnType<typeof useAcceptedKnowledge>; onCheck:()=>void; active?:boolean }) {
  const [source, setSource] = useState<string | null>(null)
  if (reading.isError) return <Card><p role="alert">Could not load your accepted knowledge material. AI help does not replace it.</p><Button onClick={() => void reading.refetch()} disabled={reading.isFetching}>Retry accepted material</Button></Card>
  if (reading.isPending) return <p role="status">Checking for your accepted knowledge material…</p>
  if (!reading.data) return null
  const data = reading.data
  return <Card>
    <CardTitle as="h2">Your accepted knowledge material</CardTitle>
    <p className="text-sm mb-3">Saved lesson version {data.learning_object_version}. This shows the material you activated, without AI rewriting. Acceptance is not independent factual verification.</p>
    <LessonReader identity={`accepted-knowledge:${data.draft_id}:${data.learning_object_version}`}
      text={`## Explanation\n\n${data.explanation}\n\n## A worked example\n\n${data.worked_example}`}
      active={active} sources={data.sources.map(id => ({chunk_id:id, citation:'Uploaded reference', cited:false}))} />
    <Disclosure label="Your notes and source references"><Markdown text={data.notes} />
      {data.sources.map((id,index)=><Button key={id} variant="secondary" onClick={()=>setSource(id)}>Read uploaded source {index+1}</Button>)}
      {source && <SourceViewer chunkId={source} citation={data.title} onClose={()=>setSource(null)} />}
    </Disclosure>
    <div className="flex flex-wrap gap-3 mt-3"><Button onClick={onCheck}>Try this lesson</Button>
      <Link className="underline" to={`/curriculum?draft=${data.draft_id}`}>Review or revise your material</Link></div>
  </Card>
}
export function OptionalKnowledgeTutor({ authored, children }: { authored:boolean; children:ReactNode }) {
  return authored ? <Disclosure label="Optional AI tutor help"><p className="mb-3">Generated explanations can be mistaken and do not replace your accepted material above.</p>{children}</Disclosure> : <>{children}</>
}
