import { act, fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { KnowledgeAuthoring } from './KnowledgeAuthoring'
import { jsonResponse } from '../../test/utils'

const onOpen = vi.fn()
function mount(draft?: Parameters<typeof KnowledgeAuthoring>[0]["draft"], cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  return render(<QueryClientProvider client={cache}>
    <MemoryRouter><KnowledgeAuthoring draft={draft} onOpen={onOpen} /></MemoryRouter>
  </QueryClientProvider>)
}
beforeEach(() => { sessionStorage.clear(); onOpen.mockReset() })
afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

it.each([1, 4])('updates the saved draft cache promptly while preserving a newer cached version (%i)', async cachedVersion => {
  const form = { title: 'Cache test', domain: 'ai_ml', notes: 'My notes', upload_id: null,
    objective: '', explanation: '', worked_example: '', question: '', criteria: [], research: null }
  const draft = { id: 'cache1', status: 'draft', version: 1, payload: { authoring: form } } as unknown as NonNullable<Parameters<typeof KnowledgeAuthoring>[0]['draft']>
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  cache.setQueryData(['curriculum', 'drafts'], { drafts: [{ ...draft, version: cachedVersion }] })
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    return jsonResponse({ ...draft, version: 2 })
  }))
  mount(draft, cache)
  fireEvent.click(await screen.findByText('Save knowledge material'))
  await screen.findByText('Knowledge material saved. You can return later or shape it into a lesson.')
  const saved = cache.getQueryData<{ drafts: Array<{ version: number }> }>(['curriculum', 'drafts'])
  expect(saved?.drafts[0].version).toBe(cachedVersion === 1 ? 2 : 4)
})

it('reconciles a missed save receipt only when the restored material matches the saved server copy', async () => {
  const form = { title: 'Same saved material', domain: 'ai_ml', notes: 'Same notes', upload_id: null,
    objective: '', explanation: '', worked_example: '', question: '', criteria: [], research: null }
  sessionStorage.setItem('lesson-draft:v1:knowledge:owner:receipt1', JSON.stringify({ form,
    requestId: crypto.randomUUID(), baseVersion: 1 }))
  let sent: Record<string, unknown> | undefined
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    sent = JSON.parse(init!.body as string)
    return jsonResponse({ id: 'receipt1', status: 'draft', version: 3, payload: { authoring: sent } })
  }))
  const draft = { id: 'receipt1', status: 'draft', version: 2, payload: { authoring: { ...form } } } as unknown as Parameters<typeof KnowledgeAuthoring>[0]['draft']
  mount(draft)
  fireEvent.change(await screen.findByLabelText('Material title'), { target: { value: 'My next edit' } })
  fireEvent.click(screen.getByText('Save knowledge material'))
  await waitFor(() => expect(sent?.expected_version).toBe(2))
  expect(sent?.title).toBe('My next edit')
})

it('saves findings before tutor help, keeps the proposal separate and restores the chosen section', async () => {
  const q = { id: 'q1', prompt: 'How is the median found?', findings: 'Average the middle values.',
    evidence: 'Source passage', unresolved: '', section: 'My original paragraph', tutor_request: 'Help me write one paragraph', tutor_basis: '', tutor_exchanges: [] }
  const research = { passage: 'Average the two middle values.', topic: 'median', current: 0, questions: [q] }
  const form = { title: 'Median', notes: research.passage, domain: 'ai_ml', upload_id: null, objective: '', explanation: 'Earlier explanation.', worked_example: '', question: '', criteria: [], research }
  const draft = { id: 'tutor1', status: 'draft', version: 1, payload: { authoring: form } } as unknown as Parameters<typeof KnowledgeAuthoring>[0]['draft']
  const calls: Array<{ url: string; body: unknown }> = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    const body = JSON.parse(init!.body as string); calls.push({ url, body })
    if (url.endsWith('/research-tutor')) return jsonResponse({ ...draft, version: 3, payload: { authoring: {
      ...form, research: { ...research, questions: [{ ...q,
        tutor_basis: JSON.stringify({ passage: research.passage, topic: research.topic, question: q.prompt, findings: q.findings, evidence: q.evidence, unresolved: q.unresolved, section: q.section }),
        tutor_exchanges: [{ action: 'draft', request: q.tutor_request, model_call_id: 'call1', answer: {
          discussion: 'The source supports averaging.', source_quotes: [research.passage], needs_check: '', next_question: '', section: 'Draft paragraph.' } }],
      }] } } } })
    return jsonResponse({ ...draft, version: 2, payload: { authoring: body } })
  }))
  const view = mount(draft)
  fireEvent.click(await screen.findByText('Draft one section locally'))
  await screen.findByText('Tutor reply saved separately. Review it before changing your knowledge section.')
  expect(calls[0].url).toBe('/api/knowledge-material/drafts/tutor1')
  expect(calls[1].body).toEqual({ expected_version: 2, question_id: 'q1', action: 'draft' })
  expect(screen.getByLabelText('My knowledge section')).toHaveValue('My original paragraph')
  fireEvent.click(screen.getByText('Replace my section with tutor draft'))
  expect(screen.getByLabelText('My knowledge section')).toHaveValue('Draft paragraph.')
  view.unmount(); mount(draft)
  expect(await screen.findByLabelText('My knowledge section')).toHaveValue('Draft paragraph.')
  expect(screen.getByText('Latest tutor reply')).toBeInTheDocument()
  expect(calls).toHaveLength(2)
})

it('saves before local source questions and protects research once findings are entered', async () => {
  const form = { title: 'Strings', notes: 'Strings store text.', domain: 'programming', upload_id: null,
    objective: '', explanation: '', worked_example: '', question: '', criteria: [],
    research: { passage: 'Strings store text.', topic: 'strings', current: 0,
      questions: [{ id: 'q1', prompt: 'What is stored?', source_quote: 'Strings store text.', findings: '', evidence: '', unresolved: '', section: '' }] } }
  const draft = { id: 'research1', status: 'draft', version: 1, payload: { authoring: form } } as unknown as Parameters<typeof KnowledgeAuthoring>[0]['draft']
  const calls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    calls.push(url)
    return jsonResponse({ ...draft, version: calls.length + 1 })
  }))
  mount(draft)
  fireEvent.click(await screen.findByText('Prepare source-specific questions locally'))
  await screen.findByText(/Source-specific candidate questions saved/)
  expect(screen.getByText('Question source focus')).toBeInTheDocument()
  expect(calls).toEqual(['/api/knowledge-material/drafts/research1', '/api/knowledge-material/drafts/research1/research-questions'])
  fireEvent.change(screen.getByLabelText('My findings'), { target: { value: 'My own answer' } })
  expect(screen.getByText('Prepare source-specific questions locally')).toBeDisabled()
})

it('restores notes after navigation and saves an inactive material before generating', async () => {
  const bodies: Array<Record<string, unknown>> = []
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner', display_name: 'Owner' })
    if (url.endsWith('/suggest')) return jsonResponse({ id: 'draft1', status: 'draft', version: 2, payload: {
      authoring: { ...bodies[0], objective: 'Combine text values', explanation: 'Strings concatenate with +.',
        worked_example: "'A' + 'B' gives 'AB'.", question: "Combine 'C' and 'D'.", criteria: ['Uses concatenation'] } } })
    const body = JSON.parse(init!.body as string); bodies.push(body)
    return jsonResponse({ id: 'draft1', status: 'draft', version: 1, payload: { authoring: body } })
  })
  vi.stubGlobal('fetch', fetcher)
  const first = mount()
  fireEvent.change(await screen.findByLabelText('Material title'), { target: { value: 'My strings' } })
  fireEvent.change(screen.getByLabelText('Your notes and selected source content'), { target: { value: 'Join two strings with +.' } })
  first.unmount()
  mount()
  expect(await screen.findByLabelText('Material title')).toHaveValue('My strings')
  expect(screen.getByLabelText('Your notes and selected source content')).toHaveValue('Join two strings with +.')
  fireEvent.click(screen.getByRole('button', { name: '4. Review' }))
  fireEvent.click(screen.getByText('Prepare a local lesson proposal (optional)'))
  fireEvent.click(screen.getByRole('button', { name: 'Prepare local lesson proposal' }))
  await waitFor(() => expect(onOpen).toHaveBeenCalledWith('draft1'))
  expect(bodies[0].notes).toBe('Join two strings with +.')
  expect(fetcher.mock.calls.some(([url]) => url.includes('publish'))).toBe(false)
  fireEvent.click(screen.getByText('Shape a lesson (optional)'))
  expect(screen.getByLabelText('Learning objective')).toHaveValue('Combine text values')
})

it('imports upload content, retains its source id and preserves text on a failed save', async () => {
  let sent: Record<string, unknown> | undefined
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    if (url.endsWith('/uploads')) return jsonResponse({ document_id: 'source1', filename: 'lesson.md', text: 'Uploaded reference text.', sha256: 'hash', characters: 24 })
    sent = JSON.parse(init!.body as string)
    throw new Error('Connection lost')
  }))
  mount()
  const fileInput = await screen.findByLabelText('Upload reference content (optional)')
  fireEvent.change(fileInput, { target: { files: [new File(['Uploaded reference text.'], 'lesson.md', { type: 'text/markdown' })] } })
  await screen.findByText(/Uploaded lesson.md/)
  expect(screen.getByLabelText('Your notes and selected source content')).toHaveValue('Uploaded reference text.')
  fireEvent.click(screen.getByRole('button', { name: 'Save knowledge material' }))
  await screen.findByRole('alert')
  expect(sent?.upload_id).toBe('source1')
  expect(screen.getByLabelText('Your notes and selected source content')).toHaveValue('Uploaded reference text.')
  expect(onOpen).not.toHaveBeenCalled()
})


it('keeps the restored edit version so a stale browser draft cannot overwrite a newer save', async () => {
  const form = { title:'My notes', notes:'Earlier local content', domain:'ai_ml', upload_id:null,
    objective:'', explanation:'', worked_example:'', question:'', criteria:[] }
  sessionStorage.setItem('lesson-draft:v1:knowledge:owner:draft1', JSON.stringify({ form,
    requestId:crypto.randomUUID(), baseVersion:1 }))
  let sent: Record<string, unknown> | undefined
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({ id:'owner' })
    sent = JSON.parse(init!.body as string)
    return new Response(JSON.stringify({ error:{code:'draft_conflict',message:'Newer saved version exists.'} }), {status:409})
  }))
  mount({ id:'draft1', version:2, status:'draft', course:null, section:null, title:'My notes', origin:'knowledge_authored', problems:[], created_at:'now', updated_at:'now', published_at:null, payload:{ authoring:{...form, notes:'Newer server notes'} } } as Parameters<typeof KnowledgeAuthoring>[0]['draft'])
  fireEvent.click(await screen.findByRole('button',{name:'Save knowledge material'}))
  await screen.findByRole('alert')
  expect(sent?.expected_version).toBe(1)
  expect(screen.getByLabelText('Your notes and selected source content')).toHaveValue('Earlier local content')
})


it('preserves notes when combined upload content is too long and permits a retry after shortening', async () => {
  let uploads = 0
  const text = 'x'.repeat(119900)
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/learner/me') return jsonResponse({id:'owner'})
    uploads += 1
    return jsonResponse({document_id:'source', filename:'reference.md', text})
  }))
  mount()
  const input = await screen.findByLabelText('Your notes and selected source content')
  const original = 'n'.repeat(120)
  fireEvent.change(input, {target:{value:original}})
  const file = new File(['source'], 'reference.md', {type:'text/markdown'})
  fireEvent.change(screen.getByLabelText('Upload reference content (optional)'), {target:{files:[file]}})
  expect(await screen.findByRole('alert')).toHaveTextContent('120,000 characters together')
  expect(input).toHaveValue(original)
  expect(screen.queryByText('Uploaded source linked. Its passages remain attached to the lesson.')).not.toBeInTheDocument()
  fireEvent.change(input, {target:{value:'Short notes'}})
  fireEvent.change(screen.getByLabelText('Upload reference content (optional)'), {target:{files:[file]}})
  await screen.findByText('Uploaded source linked. Its passages remain attached to the lesson.')
  expect(input).toHaveValue('Short notes\n\n'+text)
  expect(uploads).toBe(2)
})


it('restores long valid authoring notes and escaped text after remount', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({id:'owner'})))
  const notes = '\n'.repeat(120000)
  const first = mount()
  fireEvent.change(await screen.findByLabelText('Material title'), {target:{value:'Long notes'}})
  fireEvent.change(screen.getByLabelText('Your notes and selected source content'), {target:{value:notes}})
  const stored = sessionStorage.getItem('lesson-draft:v1:knowledge:owner:new')!
  expect(stored.length).toBeGreaterThan(120000)
  expect(JSON.parse(stored).form.notes).toBe(notes)
  first.unmount()
  mount()
  expect(await screen.findByLabelText('Material title')).toHaveValue('Long notes')
  expect(screen.getByLabelText('Your notes and selected source content')).toHaveValue(notes)
})


it('offers explicit recovery for invalid saved request identity instead of an unsavable editor', async () => {
  const raw = JSON.stringify({requestId:'broken-id', form:{title:'Recovered title', notes:'Copy these notes',
    domain:'ai_ml', upload_id:null, objective:'', explanation:'', worked_example:'', question:'', criteria:[]}})
  sessionStorage.setItem('lesson-draft:v1:knowledge:owner:new', raw)
  let identity: string | undefined
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({id:'owner'})
    identity = (init?.headers as Record<string,string>)['Idempotency-Key']
    return jsonResponse({id:'fresh-draft',version:1,status:'draft',payload:{authoring:JSON.parse(init!.body as string)}})
  }))
  mount()
  expect(await screen.findByLabelText('Recover knowledge material data')).toHaveValue(raw)
  expect(screen.getByLabelText('Material title')).toBeDisabled()
  expect(onOpen).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button',{name:'Discard unreadable browser draft'}))
  fireEvent.change(screen.getByLabelText('Material title'),{target:{value:'New material'}})
  fireEvent.change(screen.getByLabelText('Your notes and selected source content'),{target:{value:'Copied notes'}})
  fireEvent.click(screen.getByRole('button',{name:'Save knowledge material'}))
  await waitFor(() => expect(onOpen).toHaveBeenCalledWith('fresh-draft'))
  expect(identity).toMatch(/^[0-9a-f-]{36}$/)
  expect(identity).not.toBe('broken-id')
})


it('stops waiting for a stalled revision without automatic retry and preserves its request identity', async () => {
  const requests: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (url === '/api/learner/me') return jsonResponse({id:'owner'})
    requests.push((init!.headers as Record<string,string>)['Idempotency-Key'])
    if (requests.length === 1) return new Promise<Response>((_, reject) => {
      init!.signal!.addEventListener('abort', () => reject(new DOMException('Aborted','AbortError')), {once:true})
    })
    return jsonResponse({id:'revision',version:1,status:'draft',payload:{}})
  }))
  mount({id:'active',version:2,status:'published',course:null,section:null,title:'Active material',
    origin:'knowledge_authored',problems:[],created_at:'now',updated_at:'now',published_at:'now',
    payload:{authoring:{title:'Active material',notes:'Accepted notes',domain:'ai_ml',upload_id:null,
      objective:'Goal',explanation:'Explanation',worked_example:'Example',question:'Question',criteria:['Criterion']}}})
  const create = await screen.findByRole('button',{name:'Create editable revision'})
  vi.useFakeTimers()
  fireEvent.click(create)
  await act(async () => {await vi.advanceTimersByTimeAsync(180001)})
  expect(screen.getByRole('alert')).toHaveTextContent('Check saved drafts for the revision')
  expect(requests).toHaveLength(1)
  expect(create).toBeEnabled()
  expect(onOpen).not.toHaveBeenCalled()
  fireEvent.click(create)
  await act(async () => {await vi.advanceTimersByTimeAsync(1)})
  expect(onOpen).toHaveBeenCalledWith('revision')
  expect(requests).toHaveLength(2)
  expect(requests[1]).toBe(requests[0])
})


it('shows one authoring step, keeps writing across navigation and restores the exact step', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => jsonResponse({ id: 'owner' })))
  const view = mount()
  fireEvent.change(await screen.findByLabelText('Material title'), { target: { value: 'My research' } })
  fireEvent.change(screen.getByLabelText('Your notes and selected source content'), { target: { value: 'Exact source notes.' } })
  fireEvent.click(screen.getByRole('button', { name: '2. Research' }))
  expect(screen.getByLabelText('Material title')).not.toBeVisible()
  expect(screen.getByLabelText('Topic to investigate')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Topic to investigate'), { target: { value: 'Evidence' } })
  fireEvent.click(screen.getByText('Use notes as passage'))
  fireEvent.click(screen.getByText('Prepare research questions'))
  fireEvent.change(screen.getByLabelText('My findings'), { target: { value: 'My exact finding.' } })
  fireEvent.click(screen.getByRole('button', { name: '3. Write' }))
  expect(screen.getByLabelText('My findings')).not.toBeVisible()
  expect(screen.getByLabelText('My knowledge section')).toBeVisible()
  fireEvent.change(screen.getByLabelText('My knowledge section'), { target: { value: 'My exact paragraph.' } })
  const { axe } = await import('vitest-axe')
  expect(await axe(view.container)).toHaveNoViolations()
  view.unmount(); mount()
  expect(await screen.findByLabelText('My knowledge section')).toBeVisible()
  expect(screen.getByLabelText('My knowledge section')).toHaveValue('My exact paragraph.')
  fireEvent.click(screen.getByRole('button', { name: '2. Research' }))
  expect(screen.getByLabelText('My findings')).toHaveValue('My exact finding.')
})


it('prepares the tutor while researching without blocking writing when readiness fails', async () => {
  const fetcher = vi.fn(async (url: string) => {
    if (url === '/api/learner/me') return jsonResponse({ id: 'owner' })
    return jsonResponse({ error: { code: 'offline', message: 'Optional preparation unavailable' } }, 503)
  })
  vi.stubGlobal('fetch', fetcher)
  const draft = { id: 'ready1', status: 'draft', version: 1, payload: { authoring: {
    title: 'Readiness', notes: 'Exact source', domain: 'ai_ml', upload_id: null,
    objective: '', explanation: '', worked_example: '', question: '', criteria: [], research: null,
  } } } as unknown as Parameters<typeof KnowledgeAuthoring>[0]['draft']
  mount(draft)
  await screen.findByLabelText('Material title')
  vi.useFakeTimers()
  fireEvent.click(screen.getByRole('button', { name: '2. Research' }))
  fireEvent.change(screen.getByLabelText('Topic to investigate'), { target: { value: 'My continuing research' } })
  await act(async () => { await vi.advanceTimersByTimeAsync(800) })
  expect(fetcher.mock.calls.some(([url]) => url.endsWith('/ready1/prepare-tutor'))).toBe(true)
  expect(screen.getByLabelText('Topic to investigate')).toBeEnabled()
  expect(screen.getByLabelText('Topic to investigate')).toHaveValue('My continuing research')
  expect(screen.queryByText('Optional preparation unavailable')).not.toBeInTheDocument()
})
