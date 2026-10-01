import { useEffect, useId, useRef, useState } from 'react'
import { Markdown } from '../../components/Markdown'
import { Button } from '../../components/ui/button'
import { ReadAloud } from '../voice/ReadAloud'
import { SourceViewer } from '../curriculum/SourceViewer'

type Source = { chunk_id: string; citation: string; cited: boolean }
type Props = { text: string; identity: string; active: boolean; sources?: Source[] }
type Section = { title: string; text: string }
type Reading = { selected: number; full: boolean; notes: Record<string, string> }

function sectionsFor(text: string): Section[] {
  // Cross-section definitions must remain in the same Markdown document.
  if (/^ {0,3}\[[^\]\n]+\]:/m.test(text)) return [{ title: 'Full explanation', text }]
  const lines = text.match(/[^\n]*\n|[^\n]+$/g) ?? []
  const sections: Section[] = []
  let part = ''
  let title = 'Introduction'
  let fence: { char: string; size: number } | null = null
  for (const line of lines) {
    const marker = /^ {0,3}(`{3,}|~{3,})(.*)/.exec(line)
    if (marker) {
      const run = marker[1]
      if (!fence) fence = { char: run[0], size: run.length }
      else if (run[0] === fence.char && run.length >= fence.size && !marker[2].trim()) fence = null
      part += line
      continue
    }
    const heading = !fence && /^ {0,3}#{1,6}[\t ]+(.+?)[\t ]*\r?\n?$/.exec(line)
    if (heading) {
      if (part.trim()) {
        sections.push({ title, text: part })
        part = line
      } else part += line
      title = heading[1].replace(/[\t ]+#+[\t ]*$/, '')
    } else part += line
  }
  if (part || !sections.length) sections.push({ title, text: part })
  return sections
}

export function LessonReader(props: Props) {
  return <Reader key={JSON.stringify([props.identity, props.text])} {...props} />
}
function Reader({ text, identity, active, sources }: Props) {
  const sections = sectionsFor(text)
  let hash = 2166136261
  for (let i = 0; i < text.length; i += 1) hash = Math.imul(hash ^ text.charCodeAt(i), 16777619)
  const storageKey = `lesson-reader:v1:${identity}:${(hash >>> 0).toString(16)}`
  const [initial] = useState(() => {
    const fresh: Reading = { selected: 0, full: sections.length < 2, notes: {} }
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return { reading: fresh, status: 'Reading position and notes stay in this browser.' }
      const saved = JSON.parse(raw)
      const value = saved.reading
      if (
        saved.text !== text ||
        !Number.isInteger(value?.selected) ||
        value.selected < 0 ||
        value.selected >= sections.length ||
        typeof value.full !== 'boolean' ||
        !value.notes ||
        typeof value.notes !== 'object' ||
        Array.isArray(value.notes) ||
        !Object.values(value.notes).every((v) => typeof v === 'string')
      )
        throw new Error('Invalid reading bookmark')
      return { reading: value as Reading, status: 'Saved reading position and notes restored.' }
    } catch {
      return { reading: fresh, status: 'Could not restore local notes. Reading is still available.' }
    }
  })
  const [reading, setReading] = useState(initial.reading)
  const [saveStatus, setSaveStatus] = useState(initial.status)
  const title = useRef<HTMLHeadingElement>(null)
  const id = useId()
  const visibleText = reading.full ? text : sections[reading.selected].text
  const noteKey = reading.full ? 'full' : String(reading.selected)
  function save(next: Reading) {
    setReading(next)
    try {
      localStorage.setItem(storageKey, JSON.stringify({ text, reading: next, sources }))
      setSaveStatus('Reading position and notes saved in this browser.')
      window.dispatchEvent(new Event('lesson-reader-saved'))
    } catch {
      setSaveStatus('Could not save in this browser. Your notes are still here; copy them before leaving.')
    }
  }
  function move(selected: number) {
    save({ ...reading, selected })
    title.current?.focus()
  }
  return (
    <section aria-label="Explanation reader" className="space-y-4">
      {sections.length > 1 && (
        <>
          <fieldset className="flex flex-wrap gap-3">
            <legend>Reading view</legend>
            <label>
              <input
                type="radio"
                name={`${id}-view`}
                checked={!reading.full}
                onChange={() => save({ ...reading, full: false })}
              />{' '}
              One section at a time
            </label>
            <label>
              <input
                type="radio"
                name={`${id}-view`}
                checked={reading.full}
                onChange={() => save({ ...reading, full: true })}
              />{' '}
              Full explanation
            </label>
          </fieldset>
          {!reading.full && (
            <label className="block">
              Choose a section
              <select
                className="block w-full"
                value={reading.selected}
                onChange={(e) => move(Number(e.target.value))}
              >
                {sections.map((s, i) => (
                  <option key={i} value={i}>
                    {i + 1}. {s.title}
                  </option>
                ))}
              </select>
            </label>
          )}
        </>
      )}
      <h3 ref={title} tabIndex={-1} className="text-lg font-semibold">
        {reading.full
          ? 'Full explanation'
          : `Section ${reading.selected + 1} of ${sections.length}: ${sections[reading.selected].title}`}
      </h3>
      <p className="text-sm text-muted">
        This is your reading position, not a completion or mastery score. Read freely and revisit any section
        before answering.
      </p>
      <Markdown text={visibleText} />
      {active && <ReadAloud key={`${reading.full}:${reading.selected}`} text={visibleText} />}
      {!reading.full && sections.length > 1 && (
        <nav aria-label="Explanation sections" className="flex flex-wrap gap-2">
          <Button disabled={reading.selected === 0} onClick={() => move(reading.selected - 1)}>
            Previous section
          </Button>
          <Button
            disabled={reading.selected === sections.length - 1}
            onClick={() => move(reading.selected + 1)}
          >
            Next section
          </Button>
        </nav>
      )}
      <label className="block">
        Your notes for this {reading.full ? 'explanation' : 'section'} (optional)
        <textarea
          className="block w-full border border-line rounded p-2"
          value={reading.notes[noteKey] ?? ''}
          onChange={(e) => save({ ...reading, notes: { ...reading.notes, [noteKey]: e.target.value } })}
          placeholder="What is the key idea? What would you like explained? These notes are not graded."
        />
      </label>
      <p role="status" className="text-sm">
        {saveStatus}
      </p>
    </section>
  )
}

type SavedNotes = { key: string; text: string; notes: Record<string, string>; sources?: Source[] }
function validSources(value: unknown): value is Source[] {
  return (
    Array.isArray(value) &&
    value.every(
      (s) =>
        s && typeof s.chunk_id === 'string' && typeof s.citation === 'string' && typeof s.cited === 'boolean',
    )
  )
}
function readSavedNotes(sessionId: string): { entries: SavedNotes[]; error: string } {
  const entries: SavedNotes[] = []
  let invalid = false
  try {
    const prefix = `lesson-reader:v1:${sessionId}:`
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i)
      if (!key?.startsWith(prefix)) continue
      try {
        const value = JSON.parse(localStorage.getItem(key) ?? 'null')
        const notes = value?.reading?.notes
        if (
          typeof value?.text !== 'string' ||
          !notes ||
          typeof notes !== 'object' ||
          Array.isArray(notes) ||
          !Object.values(notes).every((note) => typeof note === 'string')
        )
          throw new Error('Invalid saved notes')
        const count = sectionsFor(value.text).length
        if (!Object.keys(notes).every((key) => key === 'full' || (/^\d+$/.test(key) && Number(key) < count)))
          throw new Error('Invalid section')
        if (Object.values(notes).some((note) => String(note).trim()))
          entries.push({
            key,
            text: value.text,
            notes,
            sources: validSources(value.sources) ? value.sources : undefined,
          })
      } catch {
        invalid = true
      }
    }
    return {
      entries,
      error: invalid ? 'Some saved notes could not be read. Other notes remain available.' : '',
    }
  } catch {
    return {
      entries,
      error: 'Saved lesson notes are unavailable because this browser denied storage access.',
    }
  }
}

/** Session-scoped recovery, independent of the current in-memory tutor turn. */
export function SavedLessonNotes({ sessionId }: { sessionId: string }) {
  return <NotesArchive key={sessionId} sessionId={sessionId} />
}
function NotesArchive({ sessionId }: { sessionId: string }) {
  const [saved, setSaved] = useState(() => readSavedNotes(sessionId))
  const [openSource, setOpenSource] = useState<{ entry: string; index: number } | null>(null)
  useEffect(() => {
    const refresh = () => setSaved(readSavedNotes(sessionId))
    window.addEventListener('lesson-reader-saved', refresh)
    window.addEventListener('storage', refresh)
    return () => {
      window.removeEventListener('lesson-reader-saved', refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [sessionId])
  return (
    <details className="border border-line rounded-lg p-3">
      <summary>Saved lesson notes ({saved.entries.length})</summary>
      <p>
        Notes and explanations saved in this browser for this session. These are reading notes, not assessment
        results.
      </p>
      {saved.error && <p role="alert">{saved.error}</p>}
      {!saved.entries.length && !saved.error && <p>No notes saved for this session yet.</p>}
      {saved.entries.map((entry, index) => {
        const sections = sectionsFor(entry.text)
        return (
          <details key={entry.key} className="border border-line rounded p-3 mt-3">
            <summary>
              Explanation {index + 1}: {sections[0]?.title ?? 'Saved explanation'}
            </summary>
            {Object.entries(entry.notes)
              .filter(([, note]) => note.trim())
              .map(([key, note]) => (
                <div key={key} className="my-3">
                  <h4 className="font-semibold">
                    {key === 'full'
                      ? 'Notes on the full explanation'
                      : `Section ${Number(key) + 1}: ${sections[Number(key)].title}`}
                  </h4>
                  <p className="whitespace-pre-wrap">{note}</p>
                </div>
              ))}
            <details>
              <summary>Read the saved explanation</summary>
              <Markdown text={entry.text} />
              <h4 className="font-semibold">Saved sources</h4>
              {entry.sources === undefined ? (
                <p>
                  Source details are unavailable for this older saved explanation. Citation numbers cannot be
                  resolved here.
                </p>
              ) : entry.sources.length === 0 ? (
                <p>No source references were supplied with this explanation.</p>
              ) : (
                <ol className="list-decimal pl-6">
                  {entry.sources.map((source, i) => (
                    <li key={`${source.chunk_id}:${i}`}>
                      <p>
                        <button
                          type="button"
                          className="underline text-left"
                          onClick={() => setOpenSource({ entry: entry.key, index: i })}
                        >
                          {source.citation}
                        </button>
                        {source.cited ? '' : ' — not cited'}
                      </p>
                      <p className="text-sm break-all">Source chunk: {source.chunk_id}</p>
                      {openSource?.entry === entry.key && openSource.index === i && (
                        <SourceViewer
                          key={`${entry.key}:${i}`}
                          chunkId={source.chunk_id}
                          citation={source.citation}
                          onClose={() => setOpenSource(null)}
                        />
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </details>
          </details>
        )
      })}
    </details>
  )
}
