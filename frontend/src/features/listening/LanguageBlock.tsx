import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { usePreferences } from '../preferences/api'
import { useDueLanguage } from '../practice/api'
import { VocabPanel } from '../practice/VocabPanel'
import { ListeningPanel } from './ListeningPanel'
import { ConversationBlock } from '../voice/ConversationBlock'
import { useVoiceReadiness } from '../voice/api'
import { useListeningLessons } from './api'

/**
 * The language block (ADR-0006, whole block at a block boundary). Two concrete options when both
 * exist — due vocabulary cards, or the guided-listening lesson the learner picked under Language —
 * otherwise straight to the one that exists. The choice is the learner's; nothing auto-starts.
 */
export function LanguageBlock({ sessionId, onDone }: { sessionId: string; onDone: () => void }) {
  const prefs = usePreferences()
  const due = useDueLanguage(sessionId)
  const lessons = useListeningLessons()
  const [choice, setChoice] = useState<'vocab' | 'listening' | 'conversation' | null>(null)
  const docId = String(
    (prefs.data?.values as Record<string, unknown> | undefined)?.['listening.document_id'] ?? '',
  )
  const values = prefs.data?.values as Record<string, unknown> | undefined
  const voiceOn = values?.['voice.enabled'] === true
  const readiness = useVoiceReadiness()
  // conversation only when voice is on and the reachable voices speak that language
  const convLang =
    voiceOn && readiness.data?.conversation_lang_supported
      ? String(values?.['voice.conversation_lang'] ?? '')
      : ''
  const lesson = (lessons.data?.lessons ?? []).find((l) => l.document_id === docId)
  const left = lesson ? lesson.sections - lesson.done : 0
  const dueCount = due.data?.items.length ?? 0
  if (prefs.isLoading || lessons.isLoading || due.isLoading) return <p>Loading the language block…</p>
  if (lessons.isError) {
    return (
      <>
        <p className="text-sm text-warn" role="alert">
          Listening lessons could not be loaded ({(lessons.error as Error).message}) — showing vocabulary.
        </p>
        <VocabPanel sessionId={sessionId} onDone={onDone} />
      </>
    )
  }
  if (choice === 'listening' && lesson) {
    return <ListeningPanel sessionId={sessionId} documentId={lesson.document_id} onDone={onDone} />
  }
  if (choice === 'conversation' && convLang) {
    return <ConversationBlock sessionId={sessionId} lang={convLang} onDone={onDone} />
  }
  if (choice === 'vocab') return <VocabPanel sessionId={sessionId} onDone={onDone} />
  if ((!lesson || left === 0) && convLang) {
    return (
      <Card>
        <CardTitle>Language block — which first?</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" onClick={() => setChoice('vocab')}>
            Vocabulary ({dueCount} due)
          </Button>
          <Button variant="secondary" onClick={() => setChoice('conversation')}>
            Conversation practice ({convLang.toUpperCase()}, voice)
          </Button>
        </div>
      </Card>
    )
  }
  if (!lesson || left === 0) {
    // the learner's listening lesson is finished (or none picked): say so, then vocabulary
    return (
      <>
        {lesson && (
          <p className="text-sm text-muted" role="status">
            Guided listening: every clip of “{lesson.title}” has a saved answer — showing vocabulary.
          </p>
        )}
        <VocabPanel sessionId={sessionId} onDone={onDone} />
      </>
    )
  }
  if (dueCount === 0 && !convLang) {
    return (
      <>
        <p className="text-sm text-muted" role="status">
          No vocabulary due — showing guided listening.
        </p>
        <ListeningPanel sessionId={sessionId} documentId={lesson.document_id} onDone={onDone} />
      </>
    )
  }
  return (
    <Card>
      <CardTitle>Language block — which first?</CardTitle>
      <p className="text-sm text-muted mb-3">Both are short. Whatever you skip stays due; nothing is lost.</p>
      <div className="flex flex-wrap gap-2">
        {dueCount > 0 && (
          <Button variant="primary" onClick={() => setChoice('vocab')}>
            Vocabulary ({dueCount} due)
          </Button>
        )}
        <Button variant={dueCount > 0 ? 'secondary' : 'primary'} onClick={() => setChoice('listening')}>
          Guided listening: {lesson.title} · clip {(lesson.next_index ?? 0) + 1} of {lesson.sections}
          {lesson.media_available ? '' : ' (reading version — no audio file)'}
        </Button>
        {convLang && (
          <Button variant="secondary" onClick={() => setChoice('conversation')}>
            Conversation practice ({convLang.toUpperCase()}, voice)
          </Button>
        )}
      </div>
    </Card>
  )
}
