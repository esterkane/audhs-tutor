import { RelationshipPractice } from './ConceptRelationship'
import { CasePractice } from './CasePractice'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAcceptedKnowledge } from './acceptedKnowledgeApi'
import { Card, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { Markdown } from '../../components/Markdown'
import { LessonReader } from '../tutor/LessonReader'
import { PredictionReading } from '../tutor/PredictionReading'
import { SourceViewer } from './SourceViewer'
import { useState } from 'react'


export function AcceptedKnowledge({ reading, onCheck, active = true }: { reading:ReturnType<typeof useAcceptedKnowledge>; onCheck:()=>void; active?:boolean }) {
  const [source, setSource] = useState<string | null>(null)
  if (reading.isError) return <Card><p role="alert">Could not load your accepted knowledge material. AI help does not replace it.</p><Button onClick={() => void reading.refetch()} disabled={reading.isFetching}>Retry accepted material</Button></Card>
  if (reading.isPending) return <p role="status">Checking for your accepted knowledge material…</p>
  if (!reading.data) return null
  const data = reading.data
  const explanation = `## Explanation

${data.explanation}

`
  const text = `${explanation}## A worked example

${data.worked_example}`
  const prequestions = (data.prequestions ?? []).map(q => ({
    startOffset: q.target === 'explanation' ? 0 : explanation.length,
    identity: q.question_id, question: q.question,
    binding: { draft_id: data.draft_id, learning_object_version: data.learning_object_version, question_id: q.question_id },
  }))
  const reader = <LessonReader identity={`accepted-knowledge:${data.draft_id}:${data.learning_object_version}`}
    text={text} prequestions={prequestions}
    trail={[data.title, `Accepted lesson version ${data.learning_object_version}`]} active={active}
    sources={data.sources.map(id => ({chunk_id:id, citation:'Uploaded reference', cited:false}))} />
  return <Card>
    <CardTitle as="h2">Your accepted knowledge material</CardTitle>
    <p className="text-sm mb-3">Saved lesson version {data.learning_object_version}. This shows the material you activated, without AI rewriting. Acceptance is not independent factual verification.</p>
    {prequestions.length ? reader : <PredictionReading identity={`accepted:${data.draft_id}:${data.learning_object_version}`} title={data.title}
      resumeKeyPrefix={`lesson-reader:v1:accepted-knowledge:${data.draft_id}:${data.learning_object_version}:`}>
      {reader}
    </PredictionReading>}
    {data.relationship && <RelationshipPractice key={data.draft_id+':'+data.learning_object_version}
      identity={data.draft_id+':'+data.learning_object_version} value={data.relationship}/>}
    {data.case_comparison && <CasePractice key={data.draft_id+':'+data.learning_object_version+':'+data.case_comparison.comparison_id}
      identity={data.draft_id+':'+data.learning_object_version+':'+data.case_comparison.comparison_id} pair={data.case_comparison}/>}
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
