import { useEffect, useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card, CardTitle } from '../../components/ui/card'
import { Choice } from '../../components/ui/choice'
import { Textarea } from '../../components/ui/textarea'
import { useAttempt } from '../assess/api'
import type { AttemptResult } from '../../lib/api'
import { useMode } from '../../stores/mode'
import { useReport } from '../curriculum/api'
import { useClipTask, useLesson, useListened, useValidateTask, type TaskOut } from './api'

function mmss(t: number): string {
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

/**
 * Guided listening (P7): one bounded clip and one comprehension task at a time. Playback starts
 * only on the learner's click and stops at the clip's end; replay and "show transcript" are
 * explicit; no audio file → the transcript is the clip (reading version). The answer goes through
 * the ordinary assessment path (confidence before feedback → evidence → a scheduled card). After
 * each clip the learner chooses: next clip or stop here (stop is the primary action on low capacity).
 */
export function ListeningPanel({
  sessionId,
  documentId,
  onDone,
}: {
  sessionId: string
  documentId: string
  onDone: () => void
}) {
  const lesson = useLesson(documentId)
  const mode = useMode((s) => s.mode)
  const lowCapacity = mode === 'low_capacity'
  const [index, setIndex] = useState<number | null>(null)
  const sections = lesson.data?.sections ?? []
  const idx = index ?? lesson.data?.next_index ?? null
  const section = idx != null ? sections[idx] : undefined

  if (lesson.isLoading) return <p>Loading the lesson…</p>
  if (!lesson.data) {
    return (
      <Card>
        <p role="alert" className="text-warn text-sm">
          This lesson could not be loaded. Pick another one under Language › Listening.
        </p>
        <Button className="mt-2" onClick={onDone}>
          Continue
        </Button>
      </Card>
    )
  }
  if (idx == null || !section) {
    return (
      <Card>
        <CardTitle>Guided listening</CardTitle>
        <p className="text-sm">
          Every clip of “{lesson.data.title}” has a saved answer. Nothing more to do here today.
        </p>
        <Button variant="primary" className="mt-3" onClick={onDone}>
          Continue
        </Button>
      </Card>
    )
  }
  return (
    <ClipCard
      key={section.chunk_id}
      sessionId={sessionId}
      documentId={documentId}
      lesson={lesson.data}
      index={idx}
      lowCapacity={lowCapacity}
      onNext={() => setIndex(idx + 1 < sections.length ? idx + 1 : null)}
      onStop={onDone}
      last={idx + 1 >= sections.length}
    />
  )
}

function ClipCard({
  sessionId,
  documentId,
  lesson,
  index,
  lowCapacity,
  onNext,
  onStop,
  last,
}: {
  sessionId: string
  documentId: string
  lesson: NonNullable<ReturnType<typeof useLesson>['data']>
  index: number
  lowCapacity: boolean
  onNext: () => void
  onStop: () => void
  last: boolean
}) {
  const section = lesson.sections[index]
  const audio = useRef<HTMLAudioElement | null>(null)
  const [playing, setPlaying] = useState(false)
  const [plays, setPlays] = useState(0)
  const [replays, setReplays] = useState(0)
  const playedSeconds = useRef(0)
  const lastTick = useRef<number | null>(null)
  const [showTranscript, setShowTranscript] = useState(lesson.media_url == null)
  const [transcriptDuringTask, setTranscriptDuringTask] = useState(false)
  const titleRef = useRef<HTMLHeadingElement | null>(null)
  const [playbackError, setPlaybackError] = useState<string | null>(null)
  const listened = useListened()
  const task = useClipTask()
  const [graded, setGraded] = useState<AttemptResult | null>(null)
  const textOnly = lesson.media_url == null || playbackError != null

  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  useEffect(() => {
    const el = audio.current
    if (!el) return
    const onTime = () => {
      if (lastTick.current != null && el.currentTime > lastTick.current) {
        playedSeconds.current += Math.min(el.currentTime - lastTick.current, 2)
      }
      lastTick.current = el.currentTime
      if (el.currentTime >= section.t_end) {
        el.pause()
        el.currentTime = section.t_start
        lastTick.current = null
        setPlaying(false)
      }
    }
    const onPause = () => {
      lastTick.current = null
      setPlaying(false)
    }
    const onError = () => {
      setPlaybackError('The audio could not be played here. The transcript below is the clip.')
      setShowTranscript(true)
      setPlaying(false)
    }
    el.addEventListener('timeupdate', onTime)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onPause)
    el.addEventListener('error', onError)
    return () => {
      el.pause()
      el.removeEventListener('timeupdate', onTime)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onPause)
      el.removeEventListener('error', onError)
    }
  }, [section.t_end, section.t_start])

  async function play(fromStart: boolean) {
    const el = audio.current
    if (!el) return
    try {
      if (fromStart || el.currentTime < section.t_start || el.currentTime >= section.t_end) {
        el.currentTime = section.t_start
      }
      lastTick.current = el.currentTime
      await el.play()
      if (!el.isConnected) {
        el.pause()
        return
      }
      setPlaying(true)
      setPlays((n) => n + 1)
      if (fromStart && plays > 0) setReplays((n) => n + 1)
    } catch {
      setPlaybackError('The audio could not be played here. The transcript below is the clip.')
      setShowTranscript(true)
    }
  }

  function pause() {
    audio.current?.pause()
  }

  function stop() {
    audio.current?.pause()
    onStop()
  }

  function startTask() {
    if (task.data || task.isPending) return
    // the question trains recall: the transcript folds away (one click brings it back, counted)
    setShowTranscript(false)
    if (!textOnly && plays > 0) {
      // exposure is logged only when something was actually played — never on a button press
      listened.mutate({
        documentId,
        index,
        sessionId,
        chunkId: section.chunk_id,
        replays,
        seconds: Math.round(playedSeconds.current * 10) / 10,
      })
    }
    task.mutate({ documentId, index, sessionId, useModel: !lowCapacity })
  }

  return (
    <Card>
      <CardTitle>
        <span ref={titleRef} tabIndex={-1}>
          Guided listening · clip {index + 1} of {lesson.sections.length}
        </span>
      </CardTitle>
      <p className="text-sm text-muted">
        {lesson.title} · {mmss(section.t_start)}–{mmss(section.t_end)} (
        {Math.round(section.t_end - section.t_start)} s)
        {lesson.language ? ` · ${lesson.language.toUpperCase()}` : ''}
      </p>
      {lesson.media_url && <audio ref={audio} src={lesson.media_url} preload="none" aria-hidden="true" />}
      {textOnly ? (
        <p className="text-sm mt-2" role="status">
          {playbackError ?? lesson.media_note ?? 'No audio for this clip'} — reading version.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2 mt-3" role="group" aria-label="Playback">
          {!playing ? (
            <Button variant="primary" onClick={() => void play(false)}>
              {replays === 0 ? 'Play clip' : 'Play'}
            </Button>
          ) : (
            <Button onClick={pause}>Pause</Button>
          )}
          <Button variant="secondary" onClick={() => void play(true)}>
            Replay from start
          </Button>
          <Button variant="ghost" onClick={() => setShowTranscript((v) => !v)} aria-pressed={showTranscript}>
            {showTranscript ? 'Hide transcript' : 'Show transcript'}
          </Button>
        </div>
      )}
      {task.data && (
        <Button
          size="sm"
          variant="ghost"
          className="mt-2"
          aria-pressed={showTranscript}
          onClick={() => {
            if (!showTranscript) setTranscriptDuringTask(true)
            setShowTranscript((v) => !v)
          }}
        >
          {showTranscript ? 'Hide transcript' : 'Show transcript (counts as a hint)'}
        </Button>
      )}
      {showTranscript && (
        <blockquote
          aria-label="Transcript"
          className="text-sm mt-3 border-l-2 border-accent pl-3 whitespace-pre-wrap"
        >
          {section.text}
        </blockquote>
      )}
      {!task.data && (
        <div className="mt-4">
          <Button onClick={startTask} disabled={task.isPending}>
            {task.isPending
              ? 'Preparing the question…'
              : textOnly
                ? 'I have read it — go to the question'
                : 'Go to the question'}
          </Button>
          {task.isError && (
            <div className="mt-2">
              <p role="alert" className="text-sm text-warn">
                {(task.error as Error).message}
              </p>
              <div className="flex gap-2 mt-2">
                {!last && (
                  <Button size="sm" onClick={onNext}>
                    Skip this clip
                  </Button>
                )}
                <Button size="sm" variant="ghost" onClick={onStop}>
                  Stop here
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
      {task.data && (
        <TaskCard
          sessionId={sessionId}
          task={task.data}
          onGraded={setGraded}
          onReplay={() => void play(true)}
          canReplay={!textOnly}
          hintCount={transcriptDuringTask ? 1 : 0}
        />
      )}
      <div className="flex flex-wrap gap-2 mt-4">
        {graded && !last && (
          <Button variant={lowCapacity ? 'secondary' : 'primary'} onClick={onNext}>
            Next clip
          </Button>
        )}
        <Button variant={lowCapacity || last ? 'primary' : 'secondary'} onClick={stop}>
          {lowCapacity ? 'Stop here (enough for today)' : 'Stop here'}
        </Button>
      </div>
    </Card>
  )
}

function TaskCard({
  sessionId,
  task,
  onGraded,
  onReplay,
  canReplay,
  hintCount,
}: {
  sessionId: string
  task: TaskOut
  onGraded: (r: AttemptResult) => void
  onReplay: () => void
  canReplay: boolean
  hintCount: number
}) {
  const attempt = useAttempt()
  const report = useReport()
  const validate = useValidateTask()
  const [reported, setReported] = useState(false)
  const [validated, setValidated] = useState(false)
  const [confidence, setConfidence] = useState<number | null>(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState<AttemptResult | null>(null)

  async function sendReport() {
    await report.mutateAsync({ kind: 'wrong_item', assessment_id: item.id, note: '' })
    setReported(true)
  }

  async function markChecked() {
    await validate.mutateAsync({ assessmentId: item.id, validated: true })
    setValidated(true)
  }
  const [startedAt] = useState(() => Date.now())
  const item = task.item

  async function submit() {
    if (confidence == null || !answer) return
    const res = await attempt.mutateAsync({
      session_id: sessionId,
      assessment_id: item.id,
      answer,
      confidence_pre: confidence,
      latency_ms: Date.now() - startedAt,
      hint_count: hintCount,
    })
    setResult(res)
    onGraded(res)
  }

  return (
    <div className="mt-4 border-t border-line pt-3">
      <p className="text-sm font-medium">{item.question}</p>
      <p className="text-xs text-muted mt-1">
        {task.origin === 'model'
          ? task.validated
            ? 'Question proposed by the local model from this clip’s transcript — checked by you.'
            : 'Question proposed by the local model from this clip’s transcript — not yet checked, so it counts at half weight.'
          : 'Fill the blank with the word from the clip.'}
        {task.problems.length > 0
          ? ` The model’s question was rejected (${task.problems[0]}); this is a fill-in from the transcript.`
          : ''}
        {task.citation ? ` · ${task.citation}` : ''}
      </p>
      <div className="flex flex-wrap gap-2 mt-1">
        {task.origin === 'model' && !task.validated && !validated && (
          <Button size="sm" variant="ghost" disabled={validate.isPending} onClick={() => void markChecked()}>
            I checked this question against the clip
          </Button>
        )}
        {!reported ? (
          <Button size="sm" variant="ghost" disabled={report.isPending} onClick={() => void sendReport()}>
            Report this question as wrong
          </Button>
        ) : (
          <span className="text-xs text-muted" role="status">
            Reported — kept next to this item; nothing was rewritten.
          </span>
        )}
      </div>
      {!result ? (
        <>
          {item.options ? (
            <Choice<string>
              label="Your answer"
              options={item.options.map((o, i) => ({ value: String(i), label: o }))}
              value={answer}
              onChange={setAnswer}
              columns={1}
            />
          ) : (
            <>
              <label htmlFor="listening-answer" className="text-sm block mt-2">
                The missing word
              </label>
              <Textarea
                id="listening-answer"
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                className="min-h-10"
              />
            </>
          )}
          <div className="mt-3">
            <Choice<number>
              label="Before feedback: how confident are you? (1 = guessing, 5 = certain)"
              options={[1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }))}
              value={confidence ?? 0}
              onChange={setConfidence}
              columns={5}
            />
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            <Button
              variant="primary"
              disabled={confidence == null || !answer || attempt.isPending}
              onClick={() => void submit()}
            >
              Check
            </Button>
            {canReplay && (
              <Button variant="ghost" onClick={onReplay}>
                Replay clip first
              </Button>
            )}
          </div>
          {attempt.isError && (
            <p role="alert" className="text-sm text-warn mt-2">
              {(attempt.error as Error).message}
            </p>
          )}
        </>
      ) : (
        <div className="mt-2" role="status">
          <p className="text-sm">
            {result.correct == null ? 'Partly. ' : ''}
            {result.feedback}
          </p>
          <p className="text-sm text-muted mt-1">{result.next_step}</p>
          {result.correct === false && canReplay && (
            // the answer is on screen now: a graded retry would be a copy task, so only replay
            <Button size="sm" variant="ghost" className="mt-2" onClick={onReplay}>
              Replay the clip and say the sentence aloud
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
