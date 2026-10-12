import { createHash } from 'node:crypto'
import { expect, test, type Page } from '@playwright/test'
import { API } from './helpers'

async function fixture(page: Page, mode: 'complete' | 'partial' | 'slow' | 'reuse' = 'complete') {
  await page.route('**/api/references/*', route => route.fulfill({ json: { snapshot: null } }))
  const records = new Map<string, Record<string, unknown>>()
  const requests: { key: string; body: { question: string; parent_answer_id?: string; sources?: { passage_ids: string[]; passage_hashes: Record<string, string> } } }[] = []
  const old = { id: 'saved-example', turn_id: 'old', session_id: null, surface: 'ask', created_at: '2026-10-12T10:00:00Z', request_text: 'Why does quantization reduce memory?', learner_question: null, target_label: null, suggestion_reason: 'Local question match · You marked it helpful (not a correctness check)', source_check: { sources: [{ chunk_id: 'p1', status: 'unchanged', newer_version: true }], omitted: 0 }, context_dependent: true, preview: 'Fewer bits per weight.', skill_id: null, area_id: null, text: 'Fewer bits per weight reduce the storage required.', request: { question: 'Why does quantization reduce memory?' }, metadata: {} }
  records.set(old.id, old)
  await page.route('**/api/areas', route => route.fulfill({ json: { areas: [], total_documents: 0, unassigned_documents: 0 } }))
  await page.route('**/api/ask/suggestions?*', route => {
    const q = new URL(route.request().url()).searchParams.get('q') ?? ''
    return route.fulfill({ json: { items: q && !old.request_text.toLowerCase().includes(q.toLowerCase()) ? [] : [old], next_cursor: null } })
  })
  await page.route('**/api/answers/*', route => {
    const id = route.request().url().split('/').at(-1)!
    return records.has(id) ? route.fulfill({ json: records.get(id) }) : route.fulfill({ status: 404, json: { error: { message: 'Not found' } } })
  })
  await page.route('**/api/ask/stream', async route => {
    const body = route.request().postDataJSON() as { prefer_saved?: boolean; question: string; parent_answer_id?: string; sources?: { passage_ids: string[]; passage_hashes: Record<string, string> } }
    const key = route.request().headers()['idempotency-key']
    requests.push({ key, body })
    if (mode === 'reuse' && body.prefer_saved) return route.fulfill({ contentType: 'text/event-stream', body: `event: done\ndata: ${JSON.stringify({ text: old.text, turn_id: key, model: 'local-fixture', route: 'saved', reused: true, answer_id: old.id, saved_at: old.created_at, conversation_id: old.id })}\n\n` })
    if (mode === 'slow') { await new Promise(resolve => setTimeout(resolve, 700)); return route.abort().catch(() => undefined) }
    if (mode === 'partial' && requests.length === 1) return route.fulfill({ contentType: 'text/event-stream', body: 'event: token\ndata: {"text":"An unfinished explanation"}\n\n' })
    const id = `saved-${key}`
    const text = 'Quantization stores each weight with fewer bits. For example, eight-bit weights use less memory than 32-bit weights. Precision can decrease.'
    const record = { ...old, id, turn_id: key, request_text: body.question, text, request: body, metadata: { parent_answer_id: body.parent_answer_id ?? null, sources: body.sources ? [{ chunk_id: 'p1', citation: 'S1: Synthetic bytes (local version 1)', text: 'Eight bits use one byte.' }] : [] } }
    records.set(id, record)
    await route.fulfill({ contentType: 'text/event-stream', body: `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ text, turn_id: key, model: 'local-fixture', route: 'primary', answer_id: id, conversation_id: 'example', history_turns: body.parent_answer_id ? 1 : 0 })}\n\n` })
  })
  return requests
}

for (const width of [390, 1280]) test(`Ask preserves sessions, supports keyboard suggestions and follow-ups ${width}`, async ({ page, request }, info) => {
  const before = await (await request.get(`${API}/api/sessions/current`)).json()
  const calls = await fixture(page)
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/')
  const askEntry = page.getByRole('link', { name: 'Ask a question', exact: true })
  await expect(askEntry).toBeInViewport()
  await expect(askEntry).toHaveAccessibleDescription('Explore any area. Keeps your saved session in place.')
  await askEntry.focus()
  await expect(askEntry).toBeFocused()
  await page.screenshot({ path: info.outputPath(`home-ask-${width}.png`), fullPage: true })
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Ask the tutor', exact: true })).toBeVisible()
  await page.getByLabel('Your question', { exact: true }).fill('quant')
  await expect(page.getByText(/Local question match.*Saved/)).toBeVisible()
  await expect(page.getByText(/You marked it helpful/)).toBeVisible()
  await expect(page.getByText(/Source review needed/)).toBeVisible()
  await expect(page.getByText(/Uses earlier conversation/)).toBeVisible()
  await page.screenshot({ path: info.outputPath(`ask-suggestions-${width}.png`), fullPage: true })
  const suggestion = page.getByRole('button', { name: 'Why does quantization reduce memory?', exact: true })
  await suggestion.focus(); await page.keyboard.press('Enter')
  await expect(page.getByLabel('Your question', { exact: true })).toBeFocused()
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('Why does quantization reduce memory?')
  await page.getByRole('button', { name: 'Ask question', exact: true }).dblclick()
  await expect(page.getByRole('heading', { name: 'Why does quantization reduce memory?', exact: true })).toBeVisible()
  expect(calls).toHaveLength(1)
  await expect(page.getByText(/Saved locally/)).toBeVisible()
  await page.getByLabel('Your follow-up question').fill('Give a numerical example')
  await page.getByRole('button', { name: 'Ask follow-up', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Give a numerical example', exact: true })).toBeVisible()
  expect(calls).toHaveLength(2)
  expect(calls[1].body.parent_answer_id).toBeTruthy()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Give a numerical example', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Previous question and answer' }).click()
  await expect(page.getByRole('heading', { name: 'Why does quantization reduce memory?', exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Give a numerical example', exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'New topic or question' }).click()
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('')
  expect(await (await request.get(`${API}/api/sessions/current`)).json()).toEqual(before)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath(`ask-${width}.png`), fullPage: true })
})

test('Interrupted Ask preserves preview and reuses its request after reload', async ({ page }) => {
  const calls = await fixture(page, 'partial')
  await page.goto('/ask')
  await page.getByLabel('Your question', { exact: true }).fill('Explain precision')
  await page.getByRole('button', { name: 'Ask question', exact: true }).click()
  await expect(page.getByText('An unfinished explanation', { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText('An unfinished explanation', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Retry previous request' }).click()
  await expect(page.getByRole('heading', { name: 'Explain precision', exact: true })).toBeVisible()
  expect(calls).toHaveLength(2)
  expect(calls[0].key).toBe(calls[1].key)
})

test('Stop retains question, and denied storage preserves its retry through navigation', async ({ page }) => {
  const calls = await fixture(page, 'slow')
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = function(key, value) {
      if (key.startsWith('lesson-draft:v1:ask:') || key.startsWith('tutor-request:v1:ask:')) throw new Error('storage denied')
      return original.call(this, key, value)
    }
  })
  await page.goto('/ask')
  await page.getByLabel('Your question', { exact: true }).fill('Explain binary')
  await page.getByRole('button', { name: 'Ask question', exact: true }).click()
  await expect.poll(() => calls.length).toBe(1)
  await page.getByRole('button', { name: 'Stop response' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Stopped.' })).toBeVisible()
  await page.getByRole('link', { name: 'Home', exact: true }).click()
  await page.getByRole('link', { name: 'Ask a question', exact: true }).click()
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('Explain binary')
  await expect(page.getByRole('button', { name: 'Retry previous request' })).toBeVisible()
  expect(calls).toHaveLength(1)
  await expect(page.getByText(/Reload recovery may be unavailable/)).toBeVisible()
})

test('Saved follow-up retry survives an unavailable parent', async ({ page }) => {
  const calls = await fixture(page, 'partial')
  await page.goto('/ask?answer=saved-example')
  await page.getByLabel('Your follow-up question').fill('Explain the tradeoff')
  await page.getByRole('button', { name: 'Ask follow-up', exact: true }).click()
  await expect(page.getByText('An unfinished explanation', { exact: true })).toBeVisible()
  await page.route('**/api/answers/saved-example', route => route.fulfill({
    status: 404, json: { error: { message: 'Not found' } },
  }))
  await page.reload()
  await page.getByRole('button', { name: 'Retry previous request' }).click()
  await expect(page.getByRole('heading', { name: 'Explain the tradeoff', exact: true })).toBeVisible()
  expect(calls).toHaveLength(2)
  expect(calls[1]).toEqual(calls[0])
})

test('Ask local source review is explicit, partial and preserved on reload', async ({ page }, info) => {
  await fixture(page)
  let checks = 0
  const saved = { id: 'review-1', answer_id: 'saved-example', created_at: '2026-10-12T12:00:00Z',
    method: 'local_model_review', coverage: 'listed_claims_only', binding_status: 'unchanged',
    note: 'Local model review of listed claims only; not independent factual verification.',
    passages: [{ passage_id: 'p1', title: 'Synthetic source', document_version: 1, newer_version_available: true, binding_status: 'unchanged' }],
    proposal: { claims: [{ claim_quote: 'Fewer bits per weight reduce the storage required.', verdict: 'supported',
      explanation: 'The selected passage gives the storage relationship.', evidence: [{ passage_id: 'p1', quote: 'Eight bits use one byte.' }] }], limitations: ['Accuracy was not checked.'] } }
  await page.route('**/api/answer-checks/answer/*', route => route.fulfill({ json: { items: checks ? [saved] : [], has_more: false } }))
  await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [{ chunk_id: 'p1', citation: 'Synthetic source', text: 'Eight bits use one byte.', quarantined: false }] } }))
  await page.route('**/api/answer-checks', route => { checks++; return route.fulfill({ json: saved }) })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/ask?answer=saved-example')
  await page.getByText('Check against local sources', { exact: true }).click()
  await expect(page.getByText('No saved source reviews yet.')).toBeVisible()
  await page.getByLabel('Find local source passages').fill('bytes')
  await page.getByRole('button', { name: 'Search local library', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Synthetic source' }).focus()
  await page.keyboard.press('Space')
  expect(checks).toBe(0)
  await page.getByRole('button', { name: 'Review selected sources', exact: true }).dblclick()
  await expect(page.getByText('Model judgment: supported')).toBeVisible()
  expect(checks).toBe(1)
  await expect(page.getByText(/not independent factual verification/)).toBeVisible()
  await expect(page.getByText(/A source has a newer local version/)).toBeVisible()
  await page.reload()
  await page.getByText('Check against local sources', { exact: true }).click()
  await expect(page.getByText('Limitation: Accuracy was not checked.')).toBeVisible()
  expect(checks).toBe(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath('ask-check-mobile.png'), fullPage: true })
})

test('Source review failure preserves answer and exact retry after reload', async ({ page }) => {
  await fixture(page)
  const calls: { key: string; body: unknown }[] = []
  await page.route('**/api/answer-checks/answer/*', route => route.fulfill({ json: { items: [], has_more: false } }))
  await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [{ chunk_id: 'p1', citation: 'Synthetic source', text: 'Eight bits use one byte.', quarantined: false }] } }))
  await page.route('**/api/answer-checks', route => {
    calls.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
    return route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Temporary check failure' } } })
  })
  await page.goto('/ask?answer=saved-example')
  await page.getByText('Check against local sources', { exact: true }).click()
  await page.getByLabel('Find local source passages').fill('bytes')
  await page.getByRole('button', { name: 'Search local library', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Synthetic source' }).check()
  await page.getByRole('button', { name: 'Review selected sources', exact: true }).click()
  await expect(page.getByText('Temporary check failure', { exact: true })).toBeVisible()
  await expect(page.getByText('Fewer bits per weight reduce the storage required.', { exact: true })).toBeVisible()
  await page.reload()
  await page.getByText('Check against local sources', { exact: true }).click()
  await page.getByRole('region', { name: 'Recover tutor request' }).getByRole('button', { name: 'Retry previous request' }).click()
  await expect.poll(() => calls.length).toBe(2)
  expect(calls[1]).toEqual(calls[0])
  const body = calls[0].body as { passage_hashes: Record<string, string> }
  expect(body.passage_hashes.p1).toMatch(/^[a-f0-9]{64}$/)
})

test('Further reading stays local until an explicit external link is opened', async ({ page }, info) => {
  await fixture(page)
  const outbound: string[] = []
  page.on('request', request => {
    if (/https:\/\/(docs\.python\.org|numpy\.org|scikit-learn\.org)/.test(request.url())) outbound.push(request.url())
  })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/ask?answer=saved-example')
  await page.getByText('Further reading · official documentation', { exact: true }).click()
  await expect(page.getByText(/No reviewed link matches yet/)).toBeVisible()
  const topic = page.getByLabel('Documentation topic')
  await topic.focus()
  await topic.selectOption('numpy-basics')
  const link = page.getByRole('link', { name: 'NumPy array basics (external)' })
  await expect(link).toHaveAttribute('href', 'https://numpy.org/doc/stable/user/absolute_beginners.html')
  await expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  await expect(link).toHaveAttribute('referrerpolicy', 'no-referrer')
  await expect(page.getByText(/Optional reading, not evidence used to check this answer/)).toBeVisible()
  expect(outbound).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath('further-reading.png'), fullPage: true })
})


for (const width of [390, 1280]) test(`Ask attaches explicit sources, preserves selection on reload and renders snapshots ${width}`, async ({ page }, info) => {
  const calls = await fixture(page)
  let searches = 0
  await page.route('**/api/corpus/search', route => { searches++; return route.fulfill({ json: { hits: [{ chunk_id: 'p1', citation: 'Synthetic bytes', text: 'Eight bits use one byte.', quarantined: false }] } }) })
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/ask')
  await page.getByText('Attach local sources (optional)', { exact: true }).click()
  await page.getByLabel('Find passages in your local library').fill('bytes')
  expect(searches).toBe(0)
  await page.getByLabel('Find passages in your local library').press('Enter')
  await page.getByRole('checkbox', { name: 'Synthetic bytes', exact: true }).focus()
  await page.keyboard.press('Space')
  expect(calls).toHaveLength(0)
  await page.getByLabel('Your question', { exact: true }).fill('Explain bytes')
  await page.reload()
  await page.getByText('Attach local sources (optional) · 1 selected', { exact: true }).click()
  await expect(page.getByRole('region', { name: 'Passages attached to this question' })).toContainText('Eight bits use one byte.')
  await page.getByRole('button', { name: 'Ask question', exact: true }).dblclick()
  await expect(page.getByRole('heading', { name: 'Explain bytes', exact: true })).toBeVisible()
  expect(calls).toHaveLength(1)
  expect(calls[0].body.sources).toEqual({ passage_ids: ['p1'], passage_hashes: { p1: createHash('sha256').update('Eight bits use one byte.').digest('hex') } })
  await page.getByText('Passages supplied for this answer', { exact: true }).click()
  await expect(page.getByRole('heading', { name: 'S1: Synthetic bytes (local version 1)' })).toBeVisible()
  await expect(page.getByText('Attach local sources (optional)', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath('ask-attached-sources.png'), fullPage: true })
})


test('Stop during source hashing prevents submission and retains the draft', async ({ page }) => {
  const calls = await fixture(page)
  await page.addInitScript(() => {
    const digest = crypto.subtle.digest.bind(crypto.subtle)
    crypto.subtle.digest = async (...args) => {
      await new Promise<void>(resolve => window.addEventListener('release-test-digest', () => resolve(), { once: true }))
      return digest(...args)
    }
  })
  await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [{ chunk_id: 'p1', citation: 'Synthetic bytes', text: 'Eight bits use one byte.', quarantined: false }] } }))
  await page.goto('/ask')
  await page.getByText('Attach local sources (optional)', { exact: true }).click()
  await page.getByLabel('Find passages in your local library').fill('bytes')
  await page.getByRole('button', { name: 'Find passages', exact: true }).click()
  await page.getByRole('checkbox', { name: 'Synthetic bytes', exact: true }).check()
  await page.getByLabel('Your question', { exact: true }).fill('Explain bytes')
  await page.getByRole('button', { name: 'Ask question', exact: true }).click()
  await page.getByRole('button', { name: 'Stop response', exact: true }).click()
  await page.evaluate(() => window.dispatchEvent(new Event('release-test-digest')))
  await expect(page.getByText('Stopped before sending. Your question and selected passages are kept.', { exact: true })).toBeVisible()
  expect(calls).toHaveLength(0)
  await expect(page.getByLabel('Your question', { exact: true })).toHaveValue('Explain bytes')
  await expect(page.getByText('Attach local sources (optional) · 1 selected', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry previous request' })).toHaveCount(0)
})


test('Reference copy requires explicit download and import and preserves preview on failure', async ({ page }, info) => {
  await fixture(page)
  let downloads = 0
  let imports = 0
  const snapshot = { reference_id: 'numpy-basics', snapshot_id: 'a'.repeat(64), url: 'https://numpy.org/doc/stable/user/absolute_beginners.html', title: 'Synthetic NumPy reference', fetched_at: '2026-10-12T16:00:00Z', license_url: 'https://numpy.org/doc/stable/license.html', origin: 'third_party', extraction_version: 'html-blocks.v1', text_preview: 'Synthetic arrays have shapes. <script>not executed</script>', extracted_characters: 69, note: 'Local reading copy, not fact-checked.' }
  await page.route('**/api/references/numpy-basics/load', route => {
    downloads++
    expect(route.request().postDataJSON()).toEqual({ refresh: downloads > 1 })
    return downloads > 1 ? route.fulfill({ status: 502, json: { error: { message: 'Reference is temporarily unavailable' } } }) : route.fulfill({ json: snapshot })
  })
  await page.route('**/api/references/numpy-basics/import', route => {
    imports++
    expect(route.request().postDataJSON()).toEqual({ snapshot_id: 'a'.repeat(64) })
    return imports === 1 ? route.fulfill({ status: 503, json: { error: { message: 'Reading copy kept; local index unavailable' } } }) : route.fulfill({ json: { document_id: 'reference-doc', chunks: 1, indexed: 1, changed: true, note: 'Added to the local library as third-party material.' } })
  })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/ask?answer=saved-example')
  await page.getByText('Further reading · official documentation', { exact: true }).click()
  await page.getByLabel('Documentation topic').selectOption('numpy-basics')
  await expect(page.getByRole('button', { name: 'Save a local reading copy', exact: true })).toBeEnabled()
  expect(downloads).toBe(0); expect(imports).toBe(0)
  await page.getByRole('button', { name: 'Save a local reading copy', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(/Local reading copy saved/)).toBeVisible()
  expect(downloads).toBe(1); expect(imports).toBe(0)
  await page.getByText(/Read saved preview/).click()
  await expect(page.getByText(snapshot.text_preview, { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Add to local library', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'local index unavailable' })).toBeVisible()
  await expect(page.getByText(snapshot.text_preview, { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Add to local library', exact: true }).click()
  await expect(page.getByText(/Added to the local library as third-party material/)).toBeVisible()
  await page.getByRole('button', { name: 'Refresh reading copy', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'temporarily unavailable' })).toBeVisible()
  await expect(page.getByText(snapshot.text_preview, { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath('reference-copy-mobile.png'), fullPage: true })
})


test('Opt-in saved answer reuse is disclosed and fresh generation stays available', async ({ page }, info) => {
  const calls = await fixture(page, 'reuse')
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/ask')
  const reuse = page.getByRole('checkbox', { name: /Try a saved answer first/ })
  await expect(reuse).not.toBeChecked()
  await reuse.focus()
  await page.keyboard.press('Space')
  await expect(reuse).toBeChecked()
  await page.screenshot({ path: info.outputPath('ask-reuse-option-mobile.png'), fullPage: true })
  await page.getByLabel('Your question', { exact: true }).fill('Why does quantization reduce memory?')
  await page.getByRole('button', { name: 'Ask question', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: 'Reopened your saved answer' })).toBeVisible()
  await page.reload()
  await expect(page.getByText(/Reopened your saved answer/)).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.screenshot({ path: info.outputPath('ask-reused-mobile.png'), fullPage: true })
  await page.getByRole('link', { name: 'New topic or question' }).click()
  await expect(page.getByRole('checkbox', { name: /Try a saved answer first/ })).not.toBeChecked()
  await page.getByLabel('Your question', { exact: true }).fill('Why does quantization reduce memory?')
  await page.getByRole('button', { name: 'Ask question', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Why does quantization reduce memory?', exact: true })).toBeVisible()
  await expect(page.getByText(/Reopened your saved answer/)).toHaveCount(0)
  expect(calls).toHaveLength(2)
})
