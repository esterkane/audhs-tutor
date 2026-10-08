import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { jsonResponse, renderApp } from '../../test/utils'
import { useMode } from '../../stores/mode'
import { claimReading, updateReading, useReadingControls } from '../voice/readingOwner'
import { clearDraft, readDraft } from '../assess/draft'
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
    sessionStorage.clear()
    clearDraft('listening:s1:a1')
    clearDraft('listening:s1:a1:choice')
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

  it('pauses on replacement, preserves position, and counts no exposure while displaced', async () => {
    const posts: { url: string; body: unknown }[] = []
    stub(posts)
    const { container, unmount } = renderApp(
      <ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />,
    )
    await screen.findByRole('button', { name: 'Play clip' })
    const audio = container.querySelector('audio')!
    fireEvent.click(screen.getByRole('button', { name: 'Play clip' }))
    await screen.findByText('Playing clip.')
    audio.currentTime = 1
    fireEvent.timeUpdate(audio)
    let reading!: () => void
    act(() => {
      reading = claimReading(vi.fn())
      updateReading(reading, {
        status: 'Reading',
        ready: true,
        paused: false,
        changing: false,
        stop: vi.fn(),
        togglePause: vi.fn(),
      })
    })
    expect(audio.currentTime).toBe(1)
    expect(screen.getByText(/Clip paused because another reading started/)).toBeVisible()
    audio.currentTime = 10
    fireEvent.timeUpdate(audio)
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Playback' })).getByRole('button', { name: 'Resume clip' }),
    )
    await screen.findByText('Playing clip.')
    audio.currentTime = 11
    fireEvent.timeUpdate(audio)
    fireEvent.click(screen.getByRole('button', { name: 'Go to the question' }))
    await waitFor(() =>
      expect(posts.find((p) => p.url.endsWith('/listened'))?.body).toMatchObject({ seconds: 2, replays: 0 }),
    )
    unmount()
    expect(useReadingControls.getState().reading).toBeNull()
  })

  it('fences delayed play resolution and rejection after a replacement and newer resume', async () => {
    stub([])
    let resolveFirst!: () => void
    let rejectSecond!: (error: Error) => void
    vi.mocked(window.HTMLMediaElement.prototype.play)
      .mockImplementationOnce(
        () =>
          new Promise<void>((resolve) => {
            resolveFirst = resolve
          }),
      )
      .mockImplementationOnce(
        () =>
          new Promise<void>((_, reject) => {
            rejectSecond = reject
          }),
      )
      .mockResolvedValue(undefined)
    const { unmount } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    await screen.findByRole('button', { name: 'Play clip' })
    fireEvent.click(screen.getByRole('button', { name: 'Play clip' }))
    act(() => {
      claimReading(vi.fn())()
    })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Playback' })).getByRole('button', { name: 'Resume clip' }),
    )
    act(() => {
      claimReading(vi.fn())()
    })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Playback' })).getByRole('button', { name: 'Resume clip' }),
    )
    await screen.findByText('Playing clip.')
    vi.mocked(window.HTMLMediaElement.prototype.pause).mockClear()
    await act(async () => {
      resolveFirst()
      rejectSecond(new Error('old failure'))
    })
    expect(window.HTMLMediaElement.prototype.pause).not.toHaveBeenCalled()
    expect(screen.queryByText(/could not be played here/)).not.toBeInTheDocument()
    expect(useReadingControls.getState().reading).toMatchObject({ kind: 'clip', paused: false })
    unmount()
  })

  it('shared clip controls pause without resetting position and completion releases ownership', async () => {
    stub([])
    const { container } = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Play clip' }))
    // Playing status is published before the play promise's finally clears pending.
    await screen.findByText('Playing clip.')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Replay from start' })).toBeEnabled())
    const audio = container.querySelector('audio')!
    audio.currentTime = 4
    const controls = useReadingControls.getState().reading
    act(() => {
      if (controls?.kind === 'clip') controls.togglePause()
    })
    expect(audio.currentTime).toBe(4)
    expect(useReadingControls.getState().reading).toMatchObject({ kind: 'clip', paused: true })
    fireEvent.click(
      within(screen.getByRole('group', { name: 'Playback' })).getByRole('button', { name: 'Resume clip' }),
    )
    await screen.findByText('Playing clip.')
    audio.currentTime = 12.5
    fireEvent.timeUpdate(audio)
    expect(useReadingControls.getState().reading).toBeNull()
    expect(screen.getByText(/Clip finished/)).toBeVisible()
  })

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
  it.each([false, true])('preserves playback and safely restores the question (choices=%s)', async (choices) => {
    let state = 'active'
    let revision = 0
    let failRefresh = false
    const initial = { ...task.item, content_version: 'old', options: choices ? ['numbers', 'words'] : null }
    const submissions: unknown[] = []
    vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith('/api/listening/lessons/d1')) return jsonResponse(lesson)
      if (url.endsWith('/sections/0/task')) return jsonResponse({ ...task, item: initial })
      if (url === '/api/questions/a1/practice') {
        if (init?.method === 'POST') {
          state = JSON.parse(String(init.body)).action === 'suspend' ? 'suspended' : 'active'
          revision++
        }
        const status = { assessment_id: 'a1', state, revision, reason: null }
        return jsonResponse(init?.method === 'POST' ? status : { status, affected_reviews: 0 })
      }
      if (url.startsWith('/api/assess/items/')) return failRefresh
        ? jsonResponse({ error: { message: 'offline' } }, 503)
        : jsonResponse({ ...initial, content_version: 'fresh', options: choices ? ['words', 'numbers'] : null })
      if (url.endsWith('/api/assess/attempt')) { submissions.push(JSON.parse(String(init?.body))); return jsonResponse(graded) }
      return jsonResponse({})
    }))
    let view = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Go to the question' }))
    if (choices) fireEvent.click(await screen.findByRole('button', { name: 'words' }))
    else fireEvent.change(await screen.findByLabelText('The missing word'), { target: { value: 'numbers' } })
    view.unmount()
    view = renderApp(<ListeningPanel sessionId="s1" documentId="d1" onDone={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Go to the question' }))
    if (choices) {
      await screen.findByText(/Previous choice: words/)
      expect(screen.getByRole('button', { name: 'Check' })).toBeDisabled()
    } else expect(await screen.findByLabelText('The missing word')).toHaveValue('numbers')
    const audio = view.container.querySelector('audio')!
    audio.currentTime = 5
    fireEvent.click(screen.getByRole('button', { name: 'Question practice options' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Exclude this question' }))
    await screen.findByText('This question is excluded. Your answer and clip position are kept. Restore it before checking your answer.')
    expect(screen.getByRole('button', { name: 'Check' })).toBeDisabled()
    expect(audio.currentTime).toBe(5)
    fireEvent.click(screen.getByRole('button', { name: 'Restore this question' }))
    failRefresh = true
    fireEvent.click(await screen.findByRole('button', { name: 'Refresh restored question' }))
    await screen.findByText('Could not refresh the question. Your answer and clip position are kept. Try again.')
    failRefresh = false
    fireEvent.click(screen.getByRole('button', { name: 'Refresh restored question' }))
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Refresh restored question' })).not.toBeInTheDocument())
    expect(audio.currentTime).toBe(5)
    if (choices) {
      expect(screen.getByRole('button', { name: 'Check' })).toBeDisabled()
      expect(screen.getByText(/Previous choice: words/)).toBeVisible()
      fireEvent.click(screen.getByRole('button', { name: 'words' }))
    } else expect(screen.getByLabelText('The missing word')).toHaveValue('numbers')
    expect(submissions).toEqual([])
    fireEvent.click(screen.getByRole('button', { name: 'Check' }))
    if (!choices) fireEvent.change(screen.getByLabelText('The missing word'), { target: { value: 'new edit during grading' } })
    await screen.findByRole('button', { name: 'Next clip' })
    if (!choices) expect(readDraft('listening:s1:a1').answer).toBe('new edit during grading')
    await waitFor(() => expect(submissions).toEqual([expect.objectContaining({ content_version: 'fresh', answer: choices ? '0' : 'numbers' })]))
  })

})
