import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '../../components/ui/button'
import { parseProgram, type Section } from '../programs/manifest'
import type { LessonCheckpoint } from './lessonCheckpoint'

const labels = {
  amplitude: 'Amplitude',
  frequency: 'Frequency',
  harmonics: 'Harmonics',
  sampling: 'Sampling and FFT',
  mapping: 'Audio to animation',
  create: 'Create a personal visual',
}
export function ProjectAudioContext({
  courseId,
  sectionId,
  expectedLesson,
  onOpen,
  disabled,
}: {
  courseId: string | null
  sectionId: string | null
  expectedLesson: string | null
  onOpen: (step: LessonCheckpoint['step']) => void
  disabled: boolean
}) {
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState<{ identity: string; section?: Section; error?: string } | null>(null)
  const identity = JSON.stringify([courseId, sectionId, expectedLesson])
  useEffect(() => {
    const controller = new AbortController()
    const deadline = setTimeout(() => {
      controller.abort()
      setResult({ identity, error: 'The project link took too long to load. Retry or return to projects.' })
    }, 15000)
    void fetch('/local-learning/program.json', { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error('The local project material could not be loaded.')
        const program = parseProgram(await response.json())
        const section = program.courses
          .find((c) => c.id === courseId)
          ?.sections.find((s) => s.id === sectionId)
        if (!section?.audioLab) throw new Error('This project step has no available audio-lab link.')
        if (section.audioLab.lesson !== expectedLesson)
          throw new Error('The linked audio lesson changed. Return to the project and open its current link.')
        if (!controller.signal.aborted) setResult({ identity, section })
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setResult({
            identity,
            error: error instanceof Error ? error.message : 'The project context could not be loaded.',
          })
      })
      .finally(() => clearTimeout(deadline))
    return () => {
      clearTimeout(deadline)
      controller.abort()
    }
  }, [courseId, sectionId, expectedLesson, identity, attempt])
  const current = result?.identity === identity ? result : null
  const section = current?.section
  return (
    <section className="grid gap-2 border border-line rounded-lg p-4" aria-label="Linked project experiment">
      {section?.audioLab ? (
        <>
          <Link
            className="underline"
            to={`/programs?course=${encodeURIComponent(courseId!)}&step=${encodeURIComponent(sectionId!)}`}
          >
            Return to project step: {section.title}
          </Link>
          <p>{section.audioLab.purpose}</p>
          <Button disabled={disabled} onClick={() => onOpen(section.audioLab!.lesson)}>
            Open linked lesson: {labels[section.audioLab.lesson]}
          </Button>
          <p className="text-sm text-muted">
            This opens the explanation only. Your current visual and signal settings stay in place; starting a
            test signal is a separate action.
          </p>
        </>
      ) : (
        <>
          <p role="status">{current?.error ?? 'Checking the linked project step…'}</p>
          {current?.error && (
            <Button
              onClick={() => {
                setResult(null)
                setAttempt((value) => value + 1)
              }}
            >
              Retry project link
            </Button>
          )}
          <Link to="/programs">Return to projects</Link>
        </>
      )}
    </section>
  )
}
