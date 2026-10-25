import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AuthoringSetup, FactualReviews } from './HybridAuthoring'
import { jsonResponse } from '../../test/utils'

afterEach(() => vi.unstubAllGlobals())
function wrap(node: React.ReactNode) { return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>{node}</QueryClientProvider>) }
it('saves a key without retaining it in the form or browser storage and configures the authoring-only cap', async () => {
  const bodies: Array<unknown> = []
  vi.stubGlobal('fetch',vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.body) bodies.push(JSON.parse(String(init.body)))
    return jsonResponse({enabled:false,key_configured:false,model_id:'openai-luna',daily_budget_usd:5,counted_today_usd:0})
  }))
  wrap(<AuthoringSetup />)
  fireEvent.click(screen.getByText('Authoring setup: OpenAI or local'))
  await screen.findByText(/openai-luna/)
  const key='synthetic-secret-for-form-test'
  fireEvent.change(screen.getByLabelText('OpenAI API key'),{target:{value:key}})
  fireEvent.click(screen.getByRole('button',{name:'Use OpenAI for authoring'}))
  await screen.findByText('Authoring settings saved.')
  expect(screen.getByLabelText('OpenAI API key')).toHaveValue('')
  expect(bodies).toContainEqual({key})
  expect(bodies).toContainEqual({key:'authoring.daily_budget_cents',value:500})
  expect(JSON.stringify(localStorage)).not.toContain(key)
  expect(JSON.stringify(sessionStorage)).not.toContain(key)
})
it('shows evidence and creates an update draft only after the learner requests it', async () => {
  const open=vi.fn(); const calls: string[]=[]
  vi.stubGlobal('fetch',vi.fn(async (url: string, init?: RequestInit) => {
    if(init?.method==='POST') {calls.push(url);return jsonResponse({id:'revision'})}
    return jsonResponse({id:'review',draft_id:'accepted',enabled:true,interval_days:30,urls:['https://docs.python.org/3/'],next_due_at:'tomorrow',history:[{id:'review-run',checked_at:'today',outcome:'reviewed',proposal:{findings:[{claim:'Strings are immutable',verdict:'supported',source_index:1,quote:'unchangeable',explanation:'No in-place change'}],proposed_explanation:'A revised explanation'},sources:[{url:'https://docs.python.org/3/'}]}]})
  }))
  wrap(<FactualReviews draftId="accepted" onOpen={open} />)
  fireEvent.click(screen.getByText('Factual reviews and updates (optional)'))
  await screen.findByText('unchangeable')
  expect(calls).toEqual([])
  fireEvent.click(screen.getByText('Proposed explanation'))
  fireEvent.click(screen.getByRole('button',{name:'Create update draft'}))
  await waitFor(()=>expect(open).toHaveBeenCalledWith('revision'))
  expect(calls).toEqual(['/api/knowledge-material/drafts/accepted/factual-review/revisions/review-run'])
})

it('explicitly saves the key without changing provider, cap or making a model request', async () => {
  const writes: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST' || init?.method === 'PUT') writes.push(url)
    return jsonResponse({ enabled: false, key_configured: writes.length > 0, model_id: 'openai-luna', daily_budget_usd: 5, counted_today_usd: 0 })
  }))
  wrap(<AuthoringSetup />)
  fireEvent.click(screen.getByText('Authoring setup: OpenAI or local'))
  await screen.findByText(/openai-luna/)
  expect(screen.getByRole('button', { name: 'Save API key' })).toBeDisabled()
  fireEvent.change(screen.getByLabelText('OpenAI API key'), { target: { value: 'synthetic-fixture-secret' } })
  expect(screen.getByText(/Key entered but not saved/)).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Save API key' }))
  await screen.findByText('API key saved on this machine. No model request was made.')
  expect(screen.getByLabelText('OpenAI API key')).toHaveValue('')
  expect(screen.getByText(/API key configured/)).toBeVisible()
  expect(writes).toEqual(['/api/authoring/key'])
})
it('keeps an unsaved key in the input when saving fails without claiming configuration', async () => {
  vi.stubGlobal('fetch', vi.fn(async (_url: string, init?: RequestInit) => init?.method === 'POST'
    ? jsonResponse({ error: { code: 'key_invalid', message: 'Enter a valid OpenAI API key.' } }, 422)
    : jsonResponse({ enabled: true, key_configured: false, model_id: 'openai-luna', daily_budget_usd: 5, counted_today_usd: 0 })))
  wrap(<AuthoringSetup />)
  fireEvent.click(screen.getByText('Authoring setup: OpenAI or local'))
  fireEvent.change(screen.getByLabelText('OpenAI API key'), { target: { value: 'synthetic-unsaved-key' } })
  fireEvent.click(screen.getByRole('button', { name: 'Save API key' }))
  await screen.findByText('Enter a valid OpenAI API key.')
  expect(screen.getByLabelText('OpenAI API key')).toHaveValue('synthetic-unsaved-key')
  expect(screen.getByText(/Key entered but not saved/)).toBeVisible()
  expect(screen.queryByText(/API key saved on this machine/)).not.toBeInTheDocument()
})
