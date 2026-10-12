import { expect, test, type Page } from '@playwright/test'
import { API } from './helpers'

async function fixture(page: Page, mode: 'complete' | 'partial' | 'slow' = 'complete') {
  const records = new Map<string, Record<string, unknown>>()
  const requests: { key: string; body: { question: string; parent_answer_id?: string } }[] = []
  const old = { id: 'saved-example', turn_id: 'old', session_id: null, surface: 'ask', created_at: '2026-10-12T10:00:00Z', request_text: 'Why does quantization reduce memory?', learner_question: null, target_label: null, preview: 'Fewer bits per weight.', skill_id: null, area_id: null, text: 'Fewer bits per weight reduce the storage required.', request: { question: 'Why does quantization reduce memory?' }, metadata: {} }
  records.set(old.id, old)
  await page.route('**/api/areas', route => route.fulfill({ json: { areas: [], total_documents: 0, unassigned_documents: 0 } }))
  await page.route('**/api/answers?*', route => {
    const q = new URL(route.request().url()).searchParams.get('q') ?? ''
    return route.fulfill({ json: { items: q && !old.request_text.toLowerCase().includes(q.toLowerCase()) ? [] : [old], next_cursor: null } })
  })
  await page.route('**/api/answers/*', route => {
    const id = route.request().url().split('/').at(-1)!
    return records.has(id) ? route.fulfill({ json: records.get(id) }) : route.fulfill({ status: 404, json: { error: { message: 'Not found' } } })
  })
  await page.route('**/api/ask/stream', async route => {
    const body = route.request().postDataJSON() as { question: string; parent_answer_id?: string }
    const key = route.request().headers()['idempotency-key']
    requests.push({ key, body })
    if (mode === 'slow') { await new Promise(resolve => setTimeout(resolve, 700)); return route.abort().catch(() => undefined) }
    if (mode === 'partial' && requests.length === 1) return route.fulfill({ contentType: 'text/event-stream', body: 'event: token\ndata: {"text":"An unfinished explanation"}\n\n' })
    const id = `saved-${key}`
    const text = 'Quantization stores each weight with fewer bits. For example, eight-bit weights use less memory than 32-bit weights. Precision can decrease.'
    const record = { ...old, id, turn_id: key, request_text: body.question, text, request: body, metadata: { parent_answer_id: body.parent_answer_id ?? null } }
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
  await page.getByRole('link', { name: 'Ask a question', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Ask the tutor', exact: true })).toBeVisible()
  await page.getByLabel('Your question', { exact: true }).fill('quant')
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
