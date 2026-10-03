import { apiFetch, type AssessmentView } from '../../lib/api'
import { AssessmentRecovery } from '../assess/AssessmentRecovery'
import { AssessmentSaveStatus } from '../programs/AssessmentSaveStatus'
import { AudioControls } from '../audio/AudioControls'
import { claimReading, updateReading } from '../voice/readingOwner'
import { bindMedia } from '../audio/settings'
import { OptionalConfidence } from '../../components/OptionalConfidence'
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
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
  const [starting, setStarting] = useState(false)
  const [playbackNotice, setPlaybackNotice] = useState('')
  const lease = useRef<(() => void) | null>(null)
  const operation = useRef(0)
  const activePlayback = useRef(false)
  const pendingPlay = useRef(false)
  const mounted = useRef(true)
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

  const releaseLease = useCallback(() => {
    lease.current?.()
    lease.current = null
  }, [])
  const halt = useCallback(
    (release = false) => {
      operation.current++
      pendingPlay.current = false
      activePlayback.current = false
      lastTick.current = null
      audio.current?.pause()
      if (release) releaseLease()
      setStarting(false)
      setPlaying(false)
    },
    [releaseLease],
  )

  useEffect(() => {
    titleRef.current?.focus()
  }, [])

  useEffect(() => {
    const el = audio.current
    if (!el) return
    const releaseAudio = bindMedia(el)
    const onTime = () => {
      if (activePlayback.current && lastTick.current != null && el.currentTime > lastTick.current) {
        playedSeconds.current += Math.min(el.currentTime - lastTick.current, 2)
      }
      lastTick.current = activePlayback.current ? el.currentTime : null
      if (el.currentTime >= section.t_end) {
        halt(true)
        el.currentTime = section.t_start
        setPlaybackNotice('Clip finished. Play starts from the beginning.')
      }
    }
    const onPause = () => {
      if (!el.paused) return // A queued pause event must not undo a newer play.
      activePlayback.current = false
      lastTick.current = null
      setPlaying(false)
    }
    const onEnded = () => {
      halt(true)
      setPlaybackNotice('Clip finished. Play starts from the beginning.')
    }
    const onError = () => {
      halt(true)
      setPlaybackError('The audio could not be played here. The transcript below is the clip.')
      setShowTranscript(true)
      setPlaying(false)
    }
    el.addEventListener('timeupdate', onTime)
    el.addEventListener('pause', onPause)
    el.addEventListener('ended', onEnded)
    el.addEventListener('error', onError)
    mounted.current = true
    return () => {
      mounted.current = false
      halt(true)
      pendingPlay.current = false
      activePlayback.current = false
      lastTick.current = null
      releaseLease()
      releaseAudio()
      el.pause()
      el.removeEventListener('timeupdate', onTime)
      el.removeEventListener('pause', onPause)
      el.removeEventListener('ended', onEnded)
      el.removeEventListener('error', onError)
    }
  }, [section.t_end, section.t_start, halt, releaseLease])

  async function play(fromStart: boolean) {
    const el = audio.current
    if (!el || pendingPlay.current) return
    halt(true)
    lease.current = claimReading((replacement) => {
      halt(true)
      setPlaybackNotice(`Clip paused because ${replacement} started. Resume clip keeps your position.`)
    }, 'a listening clip')
    const attempt = ++operation.current
    pendingPlay.current = true
    setStarting(true)
    setPlaybackNotice('Preparing clip…')
    try {
      if (fromStart || el.currentTime < section.t_start || el.currentTime >= section.t_end) {
        el.currentTime = section.t_start
      }
      await el.play()
      if (!mounted.current || attempt !== operation.current) {
        // A newer play owns the same element; an old promise must not pause it.
        if (!activePlayback.current && !pendingPlay.current) el.pause()
        return
      }
      activePlayback.current = true
      lastTick.current = el.currentTime
      setPlaying(true)
      setPlaybackNotice('Playing clip.')
      setPlays((n) => n + 1)
      if (fromStart && plays > 0) setReplays((n) => n + 1)
    } catch {
      if (!mounted.current || attempt !== operation.current) return
      halt(true)
      setPlaybackError('The audio could not be played here. The transcript below is the clip.')
      setShowTranscript(true)
    } finally {
      if (mounted.current && attempt === operation.current) {
        pendingPlay.current = false
        setStarting(false)
      }
    }
  }

  function pause() {
    halt()
    setPlaybackNotice('Clip paused. Resume clip keeps your position.')
  }

  function stop() {
    halt(true)
    onStop()
  }

  useEffect(() => {
    if (!lease.current) return
    updateReading(lease.current, {
      kind: 'clip',
      status: playbackNotice,
      ready: true,
      paused: !playing,
      changing: starting,
      togglePause: () => {
        if (playing) pause()
        else void play(false)
      },
      stop: () => {
        halt(true)
        setPlaybackNotice('Clip stopped. Resume clip keeps your position.')
      },
    })
  })

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
      {!textOnly && <AudioControls />}
      {playbackNotice && !textOnly && <p role="status">{playbackNotice}</p>}
      {textOnly ? (
        <p className="text-sm mt-2" role="status">
          {playbackError ?? lesson.media_note ?? 'No audio for this clip'} — reading version.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2 mt-3" role="group" aria-label="Playback">
          {!playing ? (
            <Button variant="primary" disabled={starting} onClick={() => void play(false)}>
              {starting
                ? 'Starting clip…'
                : playbackNotice.startsWith('Clip paused') || playbackNotice.startsWith('Clip stopped')
                  ? 'Resume clip'
                  : 'Play clip'}
            </Button>
          ) : (
            <Button onClick={pause}>Pause</Button>
          )}
          <Button variant="secondary" disabled={starting} onClick={() => void play(true)}>
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
          key={task.data.item.id}
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
  const attempt = useAttempt(sessionId)
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
  const [refreshedItem, setRefreshedItem] = useState<AssessmentView | null>(null)
  const [initialItem] = useState(task.item)
  const item = refreshedItem ?? initialItem
  const [previousChoice, setPreviousChoice] = useState('')
  const displayedItem = useRef(item)
  useLayoutEffect(() => {
    displayedItem.current = item
  }, [item])

  async function submit() {
    if (!answer) return
    try {
      const res = await attempt.mutateAsync({
        session_id: sessionId,
        assessment_id: item.id,
        content_version: item.content_version,
        answer,
        questionLabel: item.question,
        answerLabel: item.options?.[Number(answer)] ?? answer,
        confidence_pre: confidence,
        latency_ms: Date.now() - startedAt,
        hint_count: hintCount,
      })
      if (
        displayedItem.current.id !== item.id ||
        displayedItem.current.content_version !== item.content_version
      )
        return
      setResult(res)
      onGraded(res)
    } catch {
      // The mutation alert offers retry; preserve the answer and confidence.
    }
  }

  return (
    <div className="mt-4 border-t border-line pt-3">
      <AssessmentRecovery
        recovery={attempt.recovery}
        onRefresh={async (signal) => {
          if (attempt.recovery.pending?.body.assessment_id !== item?.id)
            throw new Error(
              'This saved answer belongs to another question. Return to that activity; the original answer is kept here.',
            )
          const latest = await apiFetch<AssessmentView>(
            `/api/assess/items/${encodeURIComponent(item.id)}?session_id=${encodeURIComponent(sessionId)}`,
            { signal },
          )
          if (signal.aborted) throw new Error('Refresh cancelled.')
          if (latest.id !== item.id) throw new Error('The refreshed question does not match.')
          if (item.options) {
            setPreviousChoice(item.options[Number(answer)] ?? answer)
            setAnswer('')
          }
          setRefreshedItem(latest)
          setResult(null)
          setValidated(false)
          setReported(false)
        }}
        onUse={(saved, body) => {
          if (
            saved.assessment_id !== item.id ||
            body.answer !== answer ||
            !body.content_version ||
            body.content_version !== item.content_version
          )
            return false
          setResult(saved)
          onGraded(saved)
          return true
        }}
      />
      {previousChoice && (
        <p role="status">
          Previous choice: {previousChoice}. The question changed; choose an option again.
        </p>
      )}
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
            <OptionalConfidence value={confidence} onChange={setConfidence} />
          </div>
          <div className="flex flex-wrap gap-2 mt-3">
            <Button variant="primary" disabled={!answer || attempt.isPending} onClick={() => void submit()}>
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
          <AssessmentSaveStatus key={result.attempt_id} result={result} />
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
