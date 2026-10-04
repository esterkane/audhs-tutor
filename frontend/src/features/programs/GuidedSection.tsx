import { RememberContext } from '../recent/RememberContext'
import { Link } from 'react-router-dom'
import { useRef, useState } from 'react'
import { Button } from '../../components/ui/button'
import { Card } from '../../components/ui/card'
import { Markdown } from '../../components/Markdown'
import { ReadAloud } from '../voice/ReadAloud'
import { TaskNotebook } from './TaskNotebook'
import { StudyTutor } from './StudyTutor'
import type { Section } from './manifest'

type Phase = 'Understand' | 'Try' | 'Think deeper'
type Work = {
  answer: string
  note: string
  label: string
  answers: Record<string, string>
  phase: Phase
  questionId: string
  practiceOrigin: string | null
}
const phases: Phase[] = ['Understand', 'Try', 'Think deeper']
type Props = { section: Section; course: string; paused: boolean; onOpenNotebook?: () => void; captureContext?: boolean; requestedTask?: boolean; onCloseTask?: () => void }
export function GuidedSection(props: Props) {
  return <Content key={`${props.course}:${props.section.id}`} {...props} />
}
function Content({ section, course, paused, onOpenNotebook, requestedTask, onCloseTask, captureContext = true }: Props) {
  const key = `project-study:v1:${course}:${section.id}`
  const practiceOrigin = section.practice
    ? JSON.stringify([section.practice.notebook, section.practice.dataset ?? null])
    : null
  const [restored] = useState(() => {
    const fresh: Work = {
      answer: '',
      note: '',
      label: 'Learning',
      answers: {},
      phase: 'Understand',
      questionId: 'original',
      practiceOrigin: null,
    }
    try {
      const value = JSON.parse(localStorage.getItem(key) ?? 'null')
      if (!value) return { work: fresh, status: '' }
      if (!['answer', 'note', 'label'].every((k) => typeof value[k] === 'string'))
        throw new Error('Invalid saved work')
      const answers =
        value.answers &&
        typeof value.answers === 'object' &&
        !Array.isArray(value.answers) &&
        Object.values(value.answers).every((a) => typeof a === 'string')
          ? value.answers
          : {}
      return {
        work: {
          ...fresh,
          answer: value.answer,
          note: value.note,
          label: value.label,
          answers,
          phase: phases.includes(value.phase) ? (value.phase as Phase) : ('Understand' as Phase),
          questionId: typeof value.questionId === 'string' ? value.questionId : 'original',
          practiceOrigin: value.practiceOrigin === practiceOrigin ? practiceOrigin : null,
        },
        status:
          value.practiceOrigin && value.practiceOrigin !== practiceOrigin
            ? 'The task notebook link changed. Your notes are restored; choose the current starter explicitly.'
            : 'Saved work restored.',
      }
    } catch {
      return { work: fresh, status: 'Saved work could not be restored. Keep a copy before leaving.' }
    }
  })
  const [work, setWork] = useState<Work>(restored.work)
  const [saved, setSaved] = useState(restored.status)
  const practiceOpen = practiceOrigin !== null && (requestedTask || work.practiceOrigin === practiceOrigin)
  const [hint, setHint] = useState(false)
  const [check, setCheck] = useState(false)
  const [tutorOpen, setTutorOpen] = useState(false)
  const heading = useRef<HTMLHeadingElement>(null)
  const questions = [
    { id: 'original', question: section.question, hint: section.hint, criteria: section.criteria },
    ...(section.challenges ?? []).map((q) => ({ ...q, id: `challenge:${q.id}` })),
  ]
  const question = questions.find((q) => q.id === work.questionId) ?? questions[0]
  const answer = question.id === 'original' ? work.answer : (work.answers[question.id] ?? '')
  function update(next: Work) {
    setWork(next)
    try {
      localStorage.setItem(key, JSON.stringify(next))
      setSaved('Saved on this browser.')
    } catch {
      setSaved('Could not save. Keep this page open and copy your work before leaving.')
    }
  }
  function choosePhase(phase: Phase) {
    update({ ...work, phase })
    setHint(false)
    setCheck(false)
    setTutorOpen(false)
    heading.current?.focus()
  }
  const activeText =
    work.phase === 'Understand'
      ? [section.explanation, section.example ?? ''].join('\n\n')
      : work.phase === 'Try'
        ? section.task
        : question.question
  // Preserve the complete passage; StudyTutor reports its API boundary visibly.
  const example = section.example ? `Worked example: ${section.example}` : ''
  const context = (
    work.phase === 'Understand'
      ? [`Explanation: ${section.explanation}`, example]
      : work.phase === 'Try'
        ? [`Task: ${section.task}`, example, `Background: ${section.explanation}`]
        : [
            `Question: ${question.question}`,
            `Criteria: ${question.criteria}`,
            example,
            `Background: ${section.explanation}`,
          ]
  )
    .filter(Boolean)
    .join('\n\n')
  const tutorAnswer = work.phase === 'Try' ? work.note : work.phase === 'Think deeper' ? answer : ''
  if (practiceOpen && section.practice)
    return (
      <div className="grid gap-3" data-capture-query={!paused && captureContext ? new URLSearchParams({ course, step: section.id, view: "task" }).toString() : undefined}>
        {!paused && captureContext && <RememberContext context={{ version: 1, kind: 'project', course_id: course, section_id: section.id, view: 'task', label: `${section.title} — task notebook`.slice(0, 200) }} />}
        <p role="status">
          {saved === 'Saved work restored.'
            ? 'Your notebook view and saved project notes were restored.'
            : saved}{' '}
          Execution results are temporary; no code runs automatically.
        </p>
        <TaskNotebook
          courseId={course}
          sectionId={section.id}
          key={`${course}:${section.id}`}
          practice={section.practice}
          identity={`${course}:${section.id}`}
          title={section.title}
          paused={paused}
          onBack={(summary) => {
            onCloseTask?.()
            update({
              ...work,
              practiceOrigin: null,
              note: summary ? [work.note, summary].filter(Boolean).join('\n\n') : work.note,
            })
            requestAnimationFrame(() => heading.current?.focus())
          }}
        />
      </div>
    )
  return (
    <Card className="grid grid-cols-1 min-w-0 gap-4 [overflow-wrap:anywhere]">
      {!paused && captureContext && <RememberContext context={{ version: 1, kind: 'project', course_id: course, section_id: section.id, view: 'guide', label: section.title.slice(0, 200) }} />}
      <p className="text-sm text-muted">
        {work.phase === 'Understand'
          ? 'Start here: read the idea and example. Then try one task.'
          : work.phase === 'Try'
            ? 'Try the task below. Ask for help whenever you need it.'
            : 'Explain your reasoning, then choose Check my answer for tutor feedback.'}
      </p>
      {section.audioLab && (
        <details>
          <summary>Related audio experiment</summary>
          <p className="text-sm my-2">{section.audioLab.purpose}</p>
          <Link
            className="underline"
            to={`/playground/visualizer?project_course=${encodeURIComponent(course)}&project_step=${encodeURIComponent(section.id)}&project_lesson=${encodeURIComponent(section.audioLab.lesson)}`}
          >
            Open linked audio lesson
          </Link>
          <p className="text-sm text-muted">
            Your work stays with this step. Opening the lab does not start sound or mark anything complete.
          </p>
        </details>
      )}
      <nav aria-label="Learning steps" className="flex flex-wrap gap-2">
        {phases.map((phase) => (
          <Button
            key={phase}
            className="min-w-0 max-w-full h-auto min-h-10 py-2 [overflow-wrap:anywhere]"
            variant={work.phase === phase ? 'primary' : 'outline'}
            aria-current={work.phase === phase ? 'step' : undefined}
            onClick={() => choosePhase(phase)}
          >
            {phase}
          </Button>
        ))}
      </nav>
      <h3 ref={heading} tabIndex={-1} className="font-semibold">
        {work.phase === 'Understand'
          ? 'The idea'
          : work.phase === 'Try'
            ? 'Your next project task'
            : 'Explain your reasoning'}
      </h3>
      {work.phase === 'Understand' && (
        <>
          <Markdown text={section.explanation} />
          {section.example && (
            <div className="border-l-4 border-line pl-4">
              <h4 className="font-semibold">Worked example</h4>
              <Markdown text={section.example} />
            </div>
          )}
          <p className="text-sm text-muted">Tutor-authored learning guide. Source: {section.source}</p>
          <Button variant="primary" onClick={() => choosePhase('Try')}>
            Try this idea
          </Button>
        </>
      )}
      {work.phase === 'Try' && (
        <>
          <Markdown text={section.task} />
          {section.practice && (
            <Button variant="primary" onClick={() => update({ ...work, practiceOrigin })}>
              Open task starter notebook
            </Button>
          )}
          {section.practice ? (
            <p className="text-sm">
              This is a small practice notebook for this step. Edit the starter code, choose Run all and
              check, then return here with results. It runs locally in this page.
            </p>
          ) : onOpenNotebook ? (
            <div className="grid gap-2">
              <p className="text-sm">
                For code or datasets, open the full course notebook tools. Return to this lesson to record
                your observations.
              </p>
              <Button onClick={onOpenNotebook}>Open full course notebook tools</Button>
            </div>
          ) : null}
          <p className="text-sm">
            Record what you tried below. These are browser-local notes, not a submitted project. Save status
            appears below.
          </p>
          <label>
            Project notes
            <textarea
              className="block border rounded p-2 w-full bg-card"
              value={work.note}
              onChange={(e) => update({ ...work, note: e.target.value })}
            />
          </label>
          <Button onClick={() => choosePhase('Think deeper')}>Explore the reasoning</Button>
        </>
      )}
      {work.phase === 'Think deeper' && (
        <>
          {questions.length > 1 && (
            <label>
              Question to explore
              <select
                className="block w-full border rounded p-2 bg-card"
                value={question.id}
                onChange={(e) => {
                  update({ ...work, questionId: e.target.value })
                  setHint(false)
                  setCheck(false)
                }}
              >
                {questions.map((q, i) => (
                  <option key={q.id} value={q.id}>
                    {i === 0 ? 'Core question' : `Deeper question ${i}`}: {q.question}
                  </option>
                ))}
              </select>
            </label>
          )}
          <Markdown text={question.question} />
          <label>
            Your explanation
            <textarea
              className="block border rounded p-2 w-full bg-card"
              value={answer}
              onChange={(e) =>
                update(
                  question.id === 'original'
                    ? { ...work, answer: e.target.value }
                    : { ...work, answers: { ...work.answers, [question.id]: e.target.value } },
                )
              }
            />
          </label>
          {!paused && (
            <StudyTutor
              courseId={course}
              sectionId={section.id}
              reviewOnly
              targetLabel={`${section.title} — ${question.question}`}
              key={`review:${question.id}`}
              identity={`${key}:review:${question.id}`}
              context={`Question: ${question.question}\nCriteria: ${question.criteria}\n${example}\nBackground: ${section.explanation}`}
              answer={answer}
            />
          )}
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setHint(!hint)}>{hint ? 'Hide hint' : 'One hint'}</Button>
            <Button onClick={() => setCheck(!check)}>
              {check ? 'Hide checklist' : 'Show self-check checklist'}
            </Button>
          </div>
          {hint && <Markdown text={question.hint} />}
          {check && (
            <div>
              <p>Self-check, not automated grading:</p>
              <Markdown text={question.criteria} />
            </div>
          )}
        </>
      )}
      {!paused && (
        <ReadAloud
          key={`${work.phase}:${question.id}`}
          text={
            work.phase === 'Think deeper'
              ? [
                  question.question,
                  hint ? `Hint: ${question.hint}` : '',
                  check ? `Self-check criteria: ${question.criteria}` : '',
                ]
                  .filter(Boolean)
                  .join('\n\n')
              : activeText
          }
          label={
            work.phase === 'Think deeper'
              ? 'Listen to question'
              : work.phase === 'Try'
                ? 'Listen to task'
                : 'Listen to explanation'
          }
        />
      )}
      <Button aria-expanded={tutorOpen} onClick={() => setTutorOpen(!tutorOpen)}>
        {tutorOpen ? 'Close tutor help' : 'Ask the tutor'}
      </Button>
      {!paused && tutorOpen && (
        <aside aria-label="Help with this step">
          <StudyTutor
            courseId={course}
            sectionId={section.id}
            targetLabel={`${section.title} — ${work.phase}`}
            key={`${work.phase}:${question.id}`}
            identity={`${key}:${work.phase}:${question.id}`}
            context={context}
            answer={tutorAnswer}
          />
        </aside>
      )}
      <details>
        <summary>Bookmark and saved work</summary>
        <label>
          My bookmark
          <select
            className="block w-full min-w-0 max-w-full border rounded p-2 bg-card"
            value={work.label}
            onChange={(e) => update({ ...work, label: e.target.value })}
          >
            <option>Learning</option>
            <option>Clear</option>
            <option>Ask later again</option>
          </select>
        </label>
        <p>Bookmarks are your reminders, not grades or mastery.</p>
      </details>
      <p role="status">{saved}</p>
    </Card>
  )
}
