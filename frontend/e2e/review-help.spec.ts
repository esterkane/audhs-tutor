import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`review help after reveal at ${width}px`, async ({ page, request }, info) => {
    await endOpenSession(request)
    await page.setViewportSize({ width, height: 900 })
    await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
    const question = 'Why compare proportions rather than retained counts?'
    await page.route('**/api/review/due?*', route => route.fulfill({ json: {
      items: [{ item_id: 'synthetic-review', skill_id: freshDeterministicSkill(), skill_title: 'Synthetic proportions',
        item_type: 'cloze', question, options: null, reveal: 'The starting group sizes can differ.',
        content_version: 'synthetic-v1', due: 'now', state: 'review' }],
      cap: 5, total_due: 1, as_of: 'now',
    } }))
    try {
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.goto('/review')
      await expect(page.getByRole('button', { name: 'Explain the idea first' })).toBeVisible()
      await page.getByRole('button', { name: 'Show answer', exact: true }).click()
      await expect(page.getByText('The starting group sizes can differ.', { exact: true })).toBeVisible()
      await expect(page.getByRole('button', { name: 'Explain the idea first' })).toHaveCount(0)
      let ratings = 0
      let generations = 0
      page.on('request', req => {
        if (req.method() === 'POST' && /\/api\/review\//.test(req.url())) ratings++
      })
      await page.route('**/api/tutor/stream', async route => {
        generations++
        expect(route.request().postDataJSON().text).toContain(question)
        const text = 'For example, 8 of 10 and 8 of 20 are different proportions.'
        const done = { turn_id: 'review-concept-help', text, outcome: 'ok', sources: [], dropped: [] }
        await route.fulfill({ contentType: 'text/event-stream', body:
          `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify(done)}\n\n` })
      })
      const help = page.locator('summary').filter({ hasText: 'Help understanding this card' })
      await help.focus()
      await page.keyboard.press('Enter')
      expect(generations).toBe(0)
      const explain = page.getByRole('button', { name: "I don't understand yet — explain the idea" })
      await explain.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('For example, 8 of 10 and 8 of 20 are different proportions.')).toBeVisible()
      await expect(page.getByText('The starting group sizes can differ.', { exact: true })).toBeVisible()
      for (const rating of ['Again', 'Hard', 'Good', 'Easy']) {
        await expect(page.getByRole('button', { name: new RegExp(`^${rating}`) })).toBeEnabled()
      }
      expect(ratings).toBe(0)
      expect(generations).toBe(1)
      await help.click()
      await help.click()
      await expect(page.getByText('For example, 8 of 10 and 8 of 20 are different proportions.')).toBeVisible()
      expect(generations).toBe(1)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('review-help-after.png'), fullPage: true })
      await page.getByRole('button', { name: 'Pause and return Home' }).click()
      await expect(page.getByRole('button', { name: /^Continue$/ })).toBeVisible()
      expect(ratings).toBe(0)
    } finally {
      await endOpenSession(request)
    }
  })
}
