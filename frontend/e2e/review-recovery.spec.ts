import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const narrow of [false, true]) {
  test(`review lost-response recovery ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
      const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(started)
      const session = await started.json()
      const next = await request.get(`${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`)
      await expectOk(next)
      const { item } = await next.json()
      expect(['mcq', 'cloze']).toContain(item.kind)
      const grade = await request.post(`${API}/api/assess/attempt`, {
        data: { session_id: session.id, assessment_id: item.id, answer: 'no idea' },
      })
      await expectOk(grade)
      const itemId = (await grade.json()).review.item_id
      const past = new Date(Date.now() - 3 * 86400000).toISOString()
      await expectOk(
        await request.post(`${API}/api/review/${itemId}?as_of=${encodeURIComponent(past)}`, {
          data: { session_id: session.id, rating: 1 },
        }),
      )
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Resume previous session/ }).click()
      await page.goto('/review')
      await page.getByRole('button', { name: 'Show answer', exact: true }).click()
      let posts = 0
      await page.route(`**/api/review/${itemId}`, async (route) => {
        posts++
        const saved = await route.fetch()
        expect(saved.ok()).toBeTruthy()
        await route.abort('failed')
      })
      await page.getByRole('button', { name: /^Good/ }).click()
      await expect(page.getByRole('button', { name: 'Check saved rating' })).toBeEnabled()
      await page.reload()
      const lookup = page.getByRole('button', { name: 'Check saved rating' })
      await expect(lookup).toBeVisible()
      await lookup.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText(/The original rating was saved/)).toBeVisible()
      await page.getByRole('button', { name: 'Update review queue' }).click()
      await expect(page.getByRole('region', { name: 'Review submission recovery' })).toHaveCount(0)
      expect(posts).toBe(1)
    } finally {
      await endOpenSession(request)
    }
  })
}
