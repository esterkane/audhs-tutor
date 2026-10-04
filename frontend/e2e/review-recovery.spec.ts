import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const beforeCommit of [false, true]) {
  for (const narrow of [false, true]) {
    test(`review ${beforeCommit ? 'before-commit failure' : 'lost-response'} recovery ${narrow ? 'narrow' : 'desktop'}`, async ({
      page,
      request,
    }) => {
      await endOpenSession(request)
      try {
        await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
        await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
        const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
        await expectOk(started)
        const session = await started.json()
        const next = await request.get(
          `${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`,
        )
        await expectOk(next)
        const { item } = await next.json()
        expect(['mcq', 'cloze']).toContain(item.kind)
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
          const response = await route.fetch()
          const data = await response.json()
          data.items = data.items.filter((card: { item_id: string }) => card.item_id === itemId)
          await route.fulfill({ response, json: data })
        })
        if (narrow) await page.setViewportSize({ width: 390, height: 844 })
        await page.goto('/')
        await page.getByRole('button', { name: /^Continue$/ }).click()
        await page.goto('/review')
        await page.getByRole('button', { name: 'Show answer', exact: true }).click()
        let posts = 0
        await page.route(`**/api/review/${itemId}`, async (route) => {
          posts++
          if (beforeCommit && posts === 1) {
            await route.fulfill({
              status: 503,
              contentType: 'application/json',
              body: JSON.stringify({
                error: { code: 'interrupted', message: 'Request interrupted before saving' },
              }),
            })
            return
          }
          const saved = await route.fetch()
          expect(saved.ok()).toBeTruthy()
          if (beforeCommit) await route.fulfill({ response: saved })
          else await route.abort('failed')
        })
        await page.getByRole('button', { name: /^Good/ }).click()
        await expect(page.getByRole('button', { name: 'Check saved rating' })).toBeEnabled()
        await page.reload()
        const lookup = page.getByRole('button', { name: 'Check saved rating' })
        await expect(lookup).toBeVisible()
        await lookup.focus()
        await page.keyboard.press('Enter')
        if (beforeCommit) {
          await expect(page.getByText(/No saved rating is visible yet/)).toBeVisible()
          await page.getByRole('button', { name: 'Send original rating', exact: true }).click()
        }
        await expect(page.getByText(/The original rating was saved/)).toBeVisible()
        await page.getByRole('button', { name: 'Update review queue' }).click()
        await expect(page.getByRole('region', { name: 'Review submission recovery' })).toHaveCount(0)
        expect(posts).toBe(beforeCommit ? 2 : 1)
      } finally {
        await endOpenSession(request)
      }
    })
  }
}
