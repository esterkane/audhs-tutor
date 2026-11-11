import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

test('a later recall can revisit a linked correction after revealing the answer', async ({
  page,
  request,
}) => {
  await endOpenSession(request)
  const start = async () => {
    const response = await request.post(API + '/api/sessions', { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    return (await response.json()).id as string
  }
  try {
    const session = await start()
    const next = await request.get(API + '/api/assess/next', {
      params: { session_id: session, skill_id: freshDeterministicSkill() },
    })
    const { item } = await next.json()
    const grade = async (answer: string, extra: Record<string, unknown> = {}) => {
      const res = await request.post(API + '/api/assess/attempt', {
        data: {
          session_id: session,
          assessment_id: item.id,
          content_version: item.content_version,
          answer,
          ...extra,
        },
      })
      await expectOk(res)
      return res.json()
    }
    const wrong = await grade('My first answer', { confidence_pre: 5 })
    expect(wrong.correct).toBe(false)
    const correctOption = item.options.find((o: string) =>
      wrong.feedback.includes('The correct option is ' + o + '.'),
    )
    expect(correctOption).toBeTruthy()
    const revision = await grade(correctOption, { revision_of_attempt_id: wrong.attempt_id })
    expect(revision.correct).toBe(true)
    expect(revision.review_updated).toBe(false)
    const id = wrong.review.item_id
    const card = await (
      await request.get(API + '/api/review/items/' + id, { params: { session_id: session } })
    ).json()
    const lookup = (session_id: string, version = card.content_version) =>
      request.get(API + '/api/review/items/' + id + '/correction', {
        params: { session_id, content_version: version },
      })
    expect(await (await lookup(session)).json()).toBeNull()
    await endOpenSession(request)
    const later = await start()
    expect(await (await lookup(later, 'stale')).json()).toBeNull()
    await page.goto('/')
    await page.getByRole('button', { name: /^Continue$/ }).click()
    // Advance only the real read-only due query; isolate this fixture card in the returned queue.
    await page.route('**/api/review/due?*', async (route) => {
      const url = new URL(route.request().url())
      url.searchParams.set('as_of', '2040-01-01T00:00:00Z')
      url.searchParams.set('all', 'true')
      const resp = await route.fetch({ url: url.toString() })
      const data = await resp.json()
      data.items = data.items.filter((i: { item_id: string }) => i.item_id === id)
      expect(data.items).toHaveLength(1)
      await route.fulfill({ response: resp, json: data })
    })
    const reads: string[] = []
    const writes: string[] = []
    page.on('request', (req) => {
      if (req.url().includes('/correction?')) reads.push(req.url())
      if (req.method() === 'POST') writes.push(req.url())
    })
    await page.goto('/review')
    const reveal = page.getByRole('button', { name: 'Show answer' })
    await expect(reveal).toBeVisible()
    expect(reads).toEqual([])
    await expect(page.getByText('Your earlier answer: My first answer')).toHaveCount(0)
    await reveal.press('Enter')
    await page.locator('summary').filter({ hasText: 'Compare with your earlier correction' }).press('Enter')
    await expect(page.getByText('Your earlier answer: My first answer')).toBeVisible()
    await expect(page.getByText('Your corrected answer after feedback: ' + correctOption)).toBeVisible()
    await expect(page.getByRole('button', { name: /^Good/ })).toBeEnabled()
    expect(writes).toEqual([])
  } finally {
    await endOpenSession(request)
  }
})
