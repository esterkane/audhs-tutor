import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test.beforeEach(async ({ request }) => {
  await endOpenSession(request)
  for (const key of ['goal.area', 'goal.course'])
    await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
})
test.afterEach(async ({ request }) => endOpenSession(request))

for (const narrow of [false, true])
  test(`lesson retry survives reload with text and draft (${narrow ? 'narrow' : 'desktop'})`, async ({
    page,
    request,
  }) => {
    if (narrow) await page.setViewportSize({ width: 390, height: 844 })
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
    await expectOk(
      await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
    )
    const calls: { key: string | undefined; body: string | null }[] = []
    await page.route('**/api/tutor/stream', async (route) => {
      calls.push({ key: route.request().headers()['idempotency-key'], body: route.request().postData() })
      const token = (text: string) => `event: token\ndata: ${JSON.stringify({ text })}\n\n`
      const body =
        calls.length === 1
          ? token('Keep this partial explanation.')
          : `event: meta\ndata: ${JSON.stringify({ replayed: true, session_id: session.id, turn_id: 'saved', hint_level: 0 })}\n\n` +
            token('Recovered full explanation.') +
            `event: done\ndata: ${JSON.stringify({ turn_id: 'saved', outcome: 'ok', text: 'Recovered full explanation.', sources: [], dropped: [], flagged: [] })}\n\n`
      await route.fulfill({ contentType: 'text/event-stream', body })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /^Continue$/ }).click()
    const input = page.getByLabel('Ask about this lesson (optional)')
    await input.fill('Explain this step')
    await page.getByRole('button', { name: 'Send lesson question' }).click()
    await expect(page.getByText('Keep this partial explanation.', { exact: true })).toBeVisible()
    await input.fill('My next unsent question')
    await page.reload()
    await expect(input).toHaveValue('My next unsent question')
    await expect(page.getByText('Keep this partial explanation.', { exact: true })).toBeVisible()
    expect(calls).toHaveLength(1)
    const retry = page.getByRole('button', { name: 'Retry previous request' })
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Recovered full explanation.', { exact: true })).toBeVisible()
    await expect(page.getByText(/Recovered the original reply/)).toBeVisible()
    await expect(input).toHaveValue('My next unsent question')
    expect(calls).toHaveLength(2)
    expect(calls[0].key).toBeTruthy()
    expect(calls[1]).toEqual(calls[0])
  })

test('a length-limited lesson stays visibly partial', async ({ page, request }, info) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
  await expectOk(response)
  const session = await response.json()
  const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
  await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
  const text = 'The explanation reached its limit while describing'
  await page.route('**/api/tutor/stream', route => route.fulfill({
    contentType: 'text/event-stream',
    body: `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ turn_id: 'limited', outcome: 'partial', text, sources: [], dropped: [], flagged: [], answer_id: null })}\n\n`,
  }))
  await page.goto('/')
  await page.getByRole('button', { name: /^Continue$/ }).click()
  await page.getByLabel('Ask about this lesson (optional)').fill('Explain this idea')
  await page.getByRole('button', { name: 'Send lesson question' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(text, { exact: true })).toBeVisible()
  await expect(page.getByText('Response interrupted. The text received so far is kept.', { exact: true })).toBeVisible()
  await page.screenshot({ path: info.outputPath('limited-lesson.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('long streaming content keeps Stop before the response on narrow screens', async ({ page, request }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
  await expectOk(response)
  const session = await response.json()
  await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: {
    session_id: session.id, index: session.plan.findIndex((block: { type: string }) => block.type === 'new_material'),
  } }))
  await page.addInitScript(() => {
    const original = window.fetch
    window.fetch = async (...args) => {
      if (String(args[0]).includes('/api/tutor/stream')) {
        const encoder = new TextEncoder()
        return new Response(new ReadableStream({ start(controller) {
          controller.enqueue(encoder.encode(`event: token\ndata: ${JSON.stringify({ text: 'Streaming example.\n\n'.repeat(80) })}\n\n`))
          args[1]?.signal?.addEventListener('abort', () => controller.error(new DOMException('Stopped', 'AbortError')), { once: true })
        } }), { headers: { 'Content-Type': 'text/event-stream' } })
      }
      return original(...args)
    }
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Continue', exact: true }).click()
  await page.getByLabel('Ask about this lesson (optional)').fill('Keep this question')
  await page.getByRole('button', { name: 'Send lesson question', exact: true }).click()
  const stop = page.getByRole('button', { name: 'Stop explanation', exact: true })
  await expect(page.getByText('Streaming example.', { exact: true })).toHaveCount(80)
  expect(await stop.evaluate(el => Boolean(el.compareDocumentPosition(document.querySelector('[aria-busy="true"]')!) & Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true)
  await stop.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Explanation stopped. Received text is kept.', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Ask about this lesson (optional)')).toHaveValue('Keep this question')
  await expect(page.getByText('Streaming example.', { exact: true })).toHaveCount(80)
})

for (const width of [390, 1280]) test(`unsaved lesson question survives storage denial and Pause ${width}`, async ({ page, request }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.addInitScript(() => {
    const write = Storage.prototype.setItem
    Storage.prototype.setItem = function (key: string, value: string) {
      if (key.startsWith('lesson-draft:')) throw new DOMException('Full', 'QuotaExceededError')
      return write.call(this, key, value)
    }
  })
  const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
  await expectOk(response)
  const session = await response.json()
  const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
  await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
  let sends = 0
  page.on('request', req => { if (req.url().endsWith('/api/tutor/stream')) sends++ })
  await page.goto('/')
  await page.getByRole('button', { name: 'Continue', exact: true }).click()
  const input = page.getByLabel('Ask about this lesson (optional)')
  await input.fill('How does this connect to my earlier example?')
  const warning = page.getByText('Your draft is kept while navigating in this tab but could not be saved for reload. Keep a copy.')
  await expect(warning).toBeVisible()
  await page.getByRole('button', { name: 'Pause and return Home', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: 'Continue', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(input).toHaveValue('How does this connect to my earlier example?')
  await expect(warning).toBeVisible()
  expect(sends).toBe(0)
  await input.focus()
  await page.screenshot({ path: info.outputPath('draft-storage-denied.png') })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await input.fill('')
  await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
  await page.getByRole('button', { name: 'Continue', exact: true }).click()
  await expect(input).toHaveValue('')
})
