import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, reachLearnBlock, skillIdBySlug } from './helpers'

for (const width of [390, 1280]) {
  test(`code exercise read failure recovers with keyboard ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      await reachLearnBlock(page)
      const session = await currentSession(request)
      const skillId = await skillIdBySlug(request, 'attn-scaled')
      await expectOk(await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, { data: { skill_id: skillId } }))
      let fail = true
      let reads = 0
      await page.route('**/api/exercises/for-skill/*', route => {
        reads++
        return fail
        ? route.fulfill({ status: 409, json: { error: { code: 'assessment_unavailable', message: 'This question is excluded from practice.' } } })
        : route.continue()
      })
      await page.setViewportSize({ width, height: 900 })
      await page.reload()
      await page.getByText(/^Code exercise \(optional/).click()
      await expect(page.getByText('Could not load the code exercise.')).toBeVisible()
      await expect(page.getByRole('link', { name: 'Manage excluded questions' })).toBeVisible()
      await page.getByLabel('Code exercise workspace').screenshot({ path: `/tmp/code-read-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      // Development StrictMode may cancel and repeat the initial read; no remount loop.
      expect(reads).toBeLessThanOrEqual(2)
      fail = false
      await page.getByRole('button', { name: 'Retry exercise' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('textbox', { name: /Your code \(Python; Tab indents/ })).toBeVisible()
      await expect(page.getByLabel('Code exercise workspace')).toBeFocused()
    } finally {
      await endOpenSession(request)
    }
  })
}
