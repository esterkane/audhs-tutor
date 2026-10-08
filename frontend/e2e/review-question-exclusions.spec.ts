import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`review question exclusion ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
    await endOpenSession(request)
    let assessmentId = ''
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
      assessmentId = item.id
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
      await page.route('**/api/review/due?*', async route => {
        const result = await route.fetch()
        const body = await result.json()
        body.items = body.items.filter((entry: { item_id: string }) => entry.item_id === itemId)
        body.total_due = body.items.length
        await route.fulfill({ response: result, json: body })
      })
      await page.setViewportSize({ width: narrow ? 390 : 1280, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.goto('/review')
      await page.getByRole('button', { name: 'Show answer', exact: true }).click()
      const options = page.getByRole('button', { name: 'Question practice options' })
      await options.focus()
      await page.keyboard.press('Enter')
      await page.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      await expect(page.getByRole('button', { name: /^Good/ })).toBeDisabled()
      await expect(page.getByText('Question choice changed. Your recall notes are kept. Refresh the queue before rating a card.')).toBeVisible()
      await page.screenshot({ path: `/tmp/review-exclusion-${narrow ? 'narrow' : 'desktop'}.png`, fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      const refresh = page.getByRole('button', { name: 'Refresh review queue' })
      await refresh.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Nothing is due right now.')).toBeVisible()
      await expect(page.getByLabel('Review workspace')).toBeFocused()
      expect(await page.evaluate(id => JSON.parse(sessionStorage.getItem(`audhs-review-queue:v1:${id}`)!).reviewed, session.id)).toEqual([])
    } finally {
      if (assessmentId) {
        const view = await (await request.get(`${API}/api/questions/${assessmentId}/practice`)).json()
        if (view.status.state === 'suspended') await expectOk(await request.post(`${API}/api/questions/${assessmentId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } }))
      }
      await endOpenSession(request)
    }
  })
}
