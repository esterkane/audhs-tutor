import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [320, 1280]) test(`learning pages expose their current activity at ${width}`, async ({ page, request }, info) => {
  await endOpenSession(request)
  await page.setViewportSize({ width, height: 900 })
  for (const [path, title] of [['/session', 'Learning session'], ['/review', 'Review'], ['/recap', 'Session recap']]) {
    await page.goto(path)
    await expect(page.locator('main h1')).toHaveText(title)
    await expect(page.getByRole('button', { name: 'Go to Home', exact: true })).toBeVisible()
  }
  try {
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    const heading = page.locator('main h1')
    await expect(heading).toHaveCount(1)
    await expect(heading).toContainText('Learn:')
    expect(await heading.evaluate(el => getComputedStyle(el).fontSize)).toBe('22px')
    await heading.scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('learning-heading.png') })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.goto('/recap')
    await expect(page.locator('main h1')).toHaveText('Finish your session')
    const save = page.getByRole('button', { name: /Save.*session|Save and finish/i })
    await save.focus()
    await page.keyboard.press('Enter')
    await expect(page.locator('main h1')).toHaveText('Session saved')
  } finally { await endOpenSession(request) }
})
