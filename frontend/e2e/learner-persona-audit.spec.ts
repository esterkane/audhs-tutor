import { writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, reachLearnBlock } from './helpers'

// Behavioral evidence, not simulated human comprehension or a learning-outcome score.
test.skip(process.env.AUDHS_UX_AUDIT !== '1', 'Opt-in Phase 4 persona walkthrough.')
for (const width of [1280, 390]) {
  test(`interrupted learner re-entry and saved-label meaning at ${width}px`, async ({ page, request, browser, baseURL }, info) => {
    await endOpenSession(request)
    try {
      for (const key of ['goal.area', 'goal.course'])
        await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
      await page.setViewportSize({ width, height: 900 })
      await reachLearnBlock(page)
      const title = await page.getByRole('heading', { name: /^Learn: / }).innerText()
      const draft = page.getByLabel('Ask about this lesson (optional)')
      await draft.fill('I do not understand the first step. Show a smaller example.')
      const checkpoint = await currentSession(request)
      await page.locator('summary').filter({ hasText: /^Change topic or save for later$/ }).click()
      await page.getByRole('button', { name: 'This is clear', exact: true }).click()
      await expect(page.getByRole('status').filter({ hasText: 'Saved as clear for you.' })).toBeVisible()
      expect(await currentSession(request)).toEqual(checkpoint)
      await page.getByRole('button', { name: 'Undo label', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Undo label', exact: true })).toHaveCount(0)
      await page.getByRole('button', { name: 'Pause and return Home', exact: true }).focus()
      await page.keyboard.press('Enter')
      await expect(page).toHaveURL(/\/$/)
      const resume = page.getByRole('button', { name: /^Continue$/ })
      await expect(resume).toHaveAccessibleDescription(/Next: return to your current learning step\./)
      const homeText = await page.getByRole('main').innerText()
      await page.screenshot({ path: info.outputPath('return-home.png'), fullPage: true })
      await resume.focus()
      await page.keyboard.press('Enter')
      await expect(draft).toHaveValue('I do not understand the first step. Show a smaller example.')
      await page.reload()
      await expect(draft).toHaveValue('I do not understand the first step. Show a smaller example.')
      expect(await currentSession(request)).toEqual(checkpoint)
      // A new context deliberately has no browser-local draft; server checkpoint survives.
      const fresh = await browser.newContext({ baseURL, viewport: { width, height: 900 }, reducedMotion: 'reduce' })
      let freshDraft = ''
      try {
        const returned = await fresh.newPage()
        await returned.goto('/')
        await returned.getByRole('button', { name: /^Continue$/ }).click()
        await expect(returned.getByRole('heading', { name: title, exact: true })).toBeVisible()
        freshDraft = await returned.getByLabel('Ask about this lesson (optional)').inputValue()
        await returned.screenshot({ path: info.outputPath('fresh-context.png'), fullPage: true })
        expect(await currentSession(request)).toEqual(checkpoint)
        expect(await returned.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      } finally { await fresh.close() }
      await writeFile(info.outputPath('observations.json'), JSON.stringify({ width, title, homeText, freshDraft, sameContextDraftRetained: true, checkpointPreserved: true, bookmarkDidNotAdvance: true, limits: 'No elapsed-week simulation, no generated response, no human comprehension measurement.' }, null, 2))
    } finally { await endOpenSession(request) }
  })
}
