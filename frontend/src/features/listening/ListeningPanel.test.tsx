import { fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { useMode } from '../../stores/mode'
import { ListeningPanel } from './ListeningPanel'

const lesson = {
  document_id: 'd1',
  title: 'Tokenisation and embeddings',
  course: 'Listening Course',
  lecture: 'Tokenisation and embeddings',
  language: 'en',
  media_url: '/api/listening/lessons/d1/media' as string | null,
  media_note: null as string | null,
  duration_s: 90,
  sections: [
    {
      index: 0,
      chunk_id: 'c1',
      t_start: 0,
      t_end: 12.5,
      text: 'Before a transformer can see text, the text has to become numbers.',
      done: false,
      attempts: 0,
    },
    {
      index: 1,
      chunk_id: 'c2',
      t_start: 12.5,
      t_end: 30,
      text: 'Second clip text here.',
      done: false,
      attempts: 0,
    },
  ],
  skipped: [],
  next_index: 0,
}
const task = {
  item: {
    id: 'a1',
    skill_id: 'n1',
    kind: 'cloze',
    question: 'the text has to become ____.',
    options: null,
    criteria: null,
    confidence_required: true,
  },
  origin: 'deterministic',
  validated: true,
  problems: [],
  citation: '[Listening Course › Inputs › Tokenisation]',
  clip: { t_start: 0, t_end: 12.5, chunk_id: 'c1' },
}
const graded = {
  attempt_id: 'x',
  assessment_id: 'a1',
  skill_id: 'n1',
  kind: 'cloze',
  dimension: 'recall',
  correct: true,
  score: 1,
  criterion_results: [],
  misconception: null,
  confidence: 1,
  grader_level: 'deterministic',
  feedback: 'The word was "numbers".',
  next_step: 'Next clip when you are ready.',
  confidence_pre: 4,
  calibration: 'calibrated',
  review: {},
  mastery: 0.3,
}

describe('ListeningPanel', () => {
  beforeEach(() => {
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(() => Promise.resolve())
    vi.spyOn(window.HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
    useMode.setState({ mode: 'steady' })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function stub(posts: { url: string; body: unknown }[], lessonBody = lesson) {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string, init?: RequestInit) => {
        if (init?.method === 'POST') posts.push({ url, body: JSON.parse(String(init.body)) })
        if (url.endsWith('/api/listening/lessons/d1')) return jsonResponse(lessonBody)
        if (url.endsWith('/sections/0/task')) return jsonResponse(task)
        if (url.endsWith('/sections/0/listened')) return new Response(null, { status: 204 })
        if (url.endsWith('/api/assess/attempt')) return jsonResponse(graded)
        if (url.endsWith('/api/curriculum/reports'))
          return jsonResponse(
            {
              id: 'r1',
              kind: 'wrong_item',
              turn_id: null,
              chunk_id: null,
              skill_id: null,
              assessment_id: 'a1',
              note: '',
              status: 'open',
              created_at: 'now',
            },
            201,
          )
        return jsonResponse({})
      }),
    )
  }

  it('plays only on click, reveals the transcript on request, asks confidence before feedback, then offers next or stop', async () => {
    const posts: { url: string; body: unknown }[] = []
    stub(posts)
    const { container } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    expect(await screen.findByText(/clip 1 of 2/)).toBeInTheDocument()
    const audio = container.querySelector('audio') as HTMLAudioElement
    expect(audio).not.toBeNull()
    expect(audio.hasAttribute('autoplay')).toBe(false)
    expect(audio.getAttribute('preload')).toBe('none')
    expect(screen.queryByText(/text has to become numbers/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Play clip' }))
    await waitFor(() => expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Show transcript' }))
    expect(screen.getByText(/text has to become numbers/)).toBeInTheDocument()
    expect(await axe(container)).toHaveNoViolations()
    fireEvent.click(screen.getByRole('button', { name: 'Go to the question' }))
    expect(await screen.findByText('the text has to become ____.')).toBeInTheDocument()
    // the transcript folds away when the question appears; reopening counts as a hint
    expect(screen.queryByText(/text has to become numbers/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Show transcript (counts as a hint)' }))
    expect(screen.getByText(/text has to become numbers/)).toBeInTheDocument()
    // exposure was logged and the task fetched, with the session id
    await waitFor(() => expect(posts.map((p) => p.url.split('/').slice(-1)[0])).toEqual(['listened', 'task']))
    expect(posts[0].body).toMatchObject({ session_id: 's1', replays: 0 }) // one play, no replay
    const check = screen.getByRole('button', { name: 'Check' })
    expect(check).toBeDisabled()
    fireEvent.change(screen.getByLabelText('The missing word'), { target: { value: 'numbers' } })
    expect(check).toBeEnabled() // confidence is optional
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '4' }))
    expect(check).toBeEnabled()
    fireEvent.click(check)
    expect(await screen.findByText(/The word was "numbers"/)).toBeInTheDocument()
    expect(posts[2].body).toMatchObject({
      assessment_id: 'a1',
      answer: 'numbers',
      confidence_pre: 4,
      hint_count: 1,
    })
    expect(screen.getByRole('button', { name: 'Next clip' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Stop here' })).toBeInTheDocument()
    // no graded retry once the answer is on screen; the wrong item can be reported
    expect(screen.queryByRole('button', { name: /Try once more/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Report this question as wrong' }))
    expect(await screen.findByText(/Reported — kept next to this item/)).toBeInTheDocument()
    expect(posts.some((p) => p.url.endsWith('/api/curriculum/reports'))).toBe(true)
    fireEvent.click(screen.getByRole('button', { name: 'Next clip' }))
    expect(await screen.findByText(/clip 2 of 2/)).toBeInTheDocument()
  })

  it('falls back to the reading version without audio and makes stopping primary on low capacity', async () => {
    useMode.setState({ mode: 'low_capacity' })
    const posts: { url: string; body: unknown }[] = []
    stub(posts, { ...lesson, media_url: null, media_note: 'no audio file next to this transcript' })
    const { container } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    expect(await screen.findByText(/reading version/)).toBeInTheDocument()
    expect(container.querySelector('audio')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Play clip' })).not.toBeInTheDocument()
    expect(screen.getByText(/text has to become numbers/)).toBeInTheDocument() // transcript is the clip
    fireEvent.click(screen.getByRole('button', { name: 'I have read it — go to the question' }))
    fireEvent.change(await screen.findByLabelText('The missing word'), { target: { value: 'numbers' } })
    // reading version: nothing was played, so no `listened` event is sent
    expect(posts.some((p) => p.url.endsWith('/listened'))).toBe(false)
    fireEvent.click(screen.getByText('Confidence (optional)'))
    fireEvent.click(screen.getByRole('button', { name: '3' }))
    fireEvent.click(screen.getByRole('button', { name: 'Check' }))
    expect(await screen.findByText(/The word was "numbers"/)).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Stop here (enough for today)' })).toBeInTheDocument()
  })

  it('allows stopping before any question or answer and pauses playback', async () => {
    const posts: { url: string; body: unknown }[] = []
    stub(posts)
    const onDone = vi.fn()
    const { unmount } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={onDone} />)
    await screen.findByText(/clip 1 of 2/)
    fireEvent.click(screen.getByRole('button', { name: 'Play clip' }))
    await waitFor(() => expect(window.HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByRole('button', { name: 'Stop here' }))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    expect(posts).toEqual([])
    vi.mocked(window.HTMLMediaElement.prototype.pause).mockClear()
    unmount()
    expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalled()
  })

  it('pauses a delayed play request if the clip was unmounted meanwhile', async () => {
    stub([])
    let finishPlay!: () => void
    vi.mocked(window.HTMLMediaElement.prototype.play).mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          finishPlay = resolve
        }),
    )
    const { unmount } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    await screen.findByText(/clip 1 of 2/)
    fireEvent.click(screen.getByRole('button', { name: 'Play clip' }))
    unmount()
    vi.mocked(window.HTMLMediaElement.prototype.pause).mockClear()
    finishPlay()
    await waitFor(() => expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalled())
  })
})

describe('ListeningPanel playback errors and keyboard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('falls back to the transcript when play() is refused and every control is a keyboard-reachable button', async () => {
    vi.spyOn(window.HTMLMediaElement.prototype, 'play').mockImplementation(() =>
      Promise.reject(new DOMException('blocked', 'NotAllowedError')),
    )
    vi.spyOn(window.HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
    useMode.setState({ mode: 'steady' })
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        if (url.endsWith('/api/listening/lessons/d1')) return jsonResponse(lesson)
        if (url.endsWith('/sections/0/task')) return jsonResponse(task)
        return jsonResponse({})
      }),
    )
    renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    const play = await screen.findByRole('button', { name: 'Play clip' })
    play.focus()
    expect(document.activeElement).toBe(play)
    fireEvent.click(play)
    expect(await screen.findByText(/could not be played here/)).toBeInTheDocument()
    expect(screen.getByText(/text has to become numbers/)).toBeInTheDocument()
    // the question button is a real button (Enter/Space work natively)
    const go = screen.getByRole('button', { name: 'I have read it — go to the question' })
    expect(go.tagName).toBe('BUTTON')
  })
})
