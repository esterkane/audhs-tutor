import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [320, 1280]) for (const theme of ['light', 'dark']) {
  test(`reading typography at ${width} ${theme}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      await page.setViewportSize({ width, height: 900 })
      for (const [key, value] of Object.entries({ 'goal.area': '', 'goal.course': '', 'ui.theme': theme, 'ui.font_scale': 'normal' }))
        await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value } }))
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: {
        session_id: session.id, index: session.plan.findIndex((block: { type: string }) => block.type === 'new_material'),
      } }))
      const text = '# Cleaning data\n\nCompare each group before removing missing values.\n\n## Inspect the groups\n\nUse `groupby` to inspect the counts.\n\n```python\ncounts = data.groupby("group").size()\nprint(counts)\n```'
      await page.route('**/api/tutor/stream', route => route.fulfill({ contentType: 'text/event-stream', body:
        `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ text, outcome: 'ok', sources: [], turn_id: 'type-fixture' })}\n\n`,
      }))
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      await page.getByRole('radio', { name: 'Full explanation', exact: true }).check()
      await expect(page.locator('main h1')).toHaveCount(1)
      const prose = page.getByRole('region', { name: 'Explanation reader' }).locator('.prose').first()
      await expect(prose).toContainText('Compare each group')
      const composer = page.getByLabel('Ask about this lesson (optional)')
      expect(await prose.evaluate(el => Boolean(el.compareDocumentPosition(document.getElementById('ask')!) & Node.DOCUMENT_POSITION_FOLLOWING))).toBe(true)
      await composer.fill('Keep my question about the groups.')
      await page.getByText('Think deeper about this explanation', { exact: true }).click()
      await page.getByRole('button', { name: 'Why does it work?', exact: true }).focus()
      await page.keyboard.press('Enter')
      await expect(composer).toBeFocused()
      await expect(composer).toContainText('Keep my question about the groups.')
      await expect(composer).toContainText('Cleaning data')

      await expect(prose.getByRole('heading', { level: 4, name: 'Cleaning data' })).toBeVisible()
      await expect(prose.getByRole('heading', { level: 5, name: 'Inspect the groups' })).toBeVisible()
      const sizes = () => prose.evaluate(element => {
        const paragraph = getComputedStyle(element.querySelector('p')!)
        const code = getComputedStyle(element.querySelector('pre code')!)
        return [getComputedStyle(document.body).fontSize, paragraph.fontSize, paragraph.lineHeight, code.fontSize, code.lineHeight].map(parseFloat)
      })
      expect(await sizes()).toEqual([14, 16, 26, 13, 20])
      const button = page.getByRole('button', { name: /^(Let me try|Return to your question)$/ })
      await button.focus()
      await expect(button).toBeFocused()
      await prose.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath('reading-type.png') })
      // Exercise the same root attribute as the existing 118% preference without leaving the lesson.
      await page.evaluate(() => { document.documentElement.dataset.font = 'large' })
      for (const [index, value] of (await sizes()).entries()) expect(value).toBeCloseTo([14, 16, 26, 13, 20][index] * 1.18, 1)
      await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
      const overflow = await page.evaluate(() => ({
        width: document.documentElement.scrollWidth,
        offenders: [...document.querySelectorAll('main *')].filter(el => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 12).map(el => ({ tag: el.tagName, class: el.className, text: el.textContent?.slice(0, 70) })),
      }))
      expect(overflow.width, JSON.stringify(overflow.offenders)).toBeLessThanOrEqual(width + 1)
    } finally {
      await endOpenSession(request)
      for (const [key, value] of Object.entries({ 'ui.theme': 'system', 'ui.font_scale': 'normal' }))
        await request.put(`${API}/api/preferences`, { data: { key, value } })
    }
  })
}
