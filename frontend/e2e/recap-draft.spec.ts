import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [1280, 390]) {
  test(`recap retains unfinished notes across reload ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
      await page.setViewportSize({ width, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.goto('/recap')
      const notes = page.getByLabel('One line for next time (optional)')
      await notes.fill('Return to the worked example and compare the two approaches.')
      await page.reload()
      await expect(notes).toHaveValue('Return to the worked example and compare the two approaches.')
      await notes.focus()
      await page.keyboard.press('End')
      await page.keyboard.type(' Next time.')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.screenshot({ path: `/tmp/recap-draft-${width}.png`, fullPage: true })
      let release!: () => void
      const held = new Promise<void>((resolve) => { release = resolve })
      await page.route('**/api/sessions/*/end', async (route) => { await held; await route.continue() })
      await page.getByRole('button', { name: 'Save and finish session', exact: true }).click()
      await expect(notes).toBeDisabled()
      release()
      await expect(page.getByRole('heading', { name: 'Session saved' })).toBeVisible()
      expect(await page.evaluate(() => Object.keys(sessionStorage).filter((key) => key.startsWith('audhs-recap:v1:')))).toEqual([])
    } finally {
      await endOpenSession(request)
    }
  })
}
