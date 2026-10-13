import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`review stale content refresh ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const next = await request.get(
        `${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`,
      )
      await expectOk(next)
      const { item } = await next.json()
      const grade = await request.post(`${API}/api/assess/attempt`, {
        data: {
          session_id: session.id,
          assessment_id: item.id,
          content_version: item.content_version,
          answer: 'no idea',
        },
      })
      await expectOk(grade)
      const itemId = (await grade.json()).review.item_id
      const shown = await request.get(`${API}/api/review/items/${itemId}?session_id=${session.id}`)
      await expectOk(shown)
      const reviewItem = await shown.json()
      const past = new Date(Date.now() - 3 * 86400000).toISOString()
      await expectOk(
        await request.post(`${API}/api/review/${itemId}?as_of=${encodeURIComponent(past)}`, {
          data: { session_id: session.id, rating: 1, content_version: reviewItem.content_version },
        }),
      )
      await page.route('**/api/review/due?*', async (route) => {
        const result = await route.fetch()
        const body = await result.json()
        body.items = body.items.filter((entry: { item_id: string }) => entry.item_id === itemId)
        body.items.forEach((entry: { content_version: string }) => {
          entry.content_version = 'ac1.old-process'
        })
        await route.fulfill({ response: result, json: body })
      })
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.evaluate(({ sessionId, id }) => {
        sessionStorage.setItem(`audhs-review:${sessionId}:${id}`, JSON.stringify({ answer: '', hints: 3 }))
      }, { sessionId: session.id, id: itemId })
      await page.goto('/review')
      await page.getByRole('button', { name: 'Show answer', exact: true }).click()
      const reject = page.waitForResponse(
        (res) => res.url().endsWith(`/api/review/${itemId}`) && res.status() === 409,
      )
      await page.getByRole('button', { name: /^Good/ }).click()
      await reject
      const refresh = page.getByRole('button', { name: 'Review updated card', exact: true })
      await refresh.focus()
      await page.keyboard.press('Enter')
      await expect(refresh).toHaveCount(0)
      await expect(page.getByRole('button', { name: /^Good/ })).toHaveCount(0)
      await page.getByRole('button', { name: 'Show answer', exact: true }).click()
      const good = page.getByRole('button', { name: /^Good/ })
      await expect(good).toBeEnabled()
      await expect(page.getByText(/check the earlier submission before trying again/)).toHaveCount(0)
      await good.focus()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.screenshot({ path: `/tmp/review-help-${narrow ? '390' : '1280'}.png`, fullPage: true })
      const accept = page.waitForResponse(
        (res) => res.url().endsWith(`/api/review/${itemId}`) && res.status() === 200,
      )
      await page.keyboard.press('Enter')
      const accepted = await accept
      expect(accepted.request().postDataJSON().hint_count).toBe(0)
    } finally {
      await endOpenSession(request)
    }
  })
}
