import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`selected lesson keeps orientation through loading and retry ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let fail = true
  await page.route('**/api/skills', async route => {
    await held
    return route.fulfill(fail ? { status: 503, json: { error: { code: 'unavailable', message: 'Catalog unavailable' } } }
      : { json: { skills: [{ id: 'chosen', title: 'Selected concept', description: 'Understand this specific concept.', unlocked: true }], next_skill_id: 'chosen' } })
  })
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  const writes: string[] = []
  page.on('request', req => { if (req.url().includes('/api/') && req.method() !== 'GET') writes.push(req.url()) })
  await page.goto('/?lesson=chosen')
  await expect(page.getByRole('heading', { level: 1, name: 'Choose a lesson' })).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: 'Checking selected lesson' })).toBeVisible()
  release()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not check the lesson' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  fail = false
  await page.getByRole('button', { name: 'Retry', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { level: 1, name: 'Learn: Selected concept' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Start this lesson' })).toBeEnabled()
  expect(writes).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('selected-lesson.png'), fullPage: true })
})
