import { expect, test } from '@playwright/test'
for (const width of [390, 1280]) test(`recent explanation and audio return ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  const writes: string[] = []
  page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/')) writes.push(request.url()) })
  await page.addInitScript(() => {
    const Original = window.AudioContext
    Object.assign(window, { audioStarts: 0 })
    window.AudioContext = new Proxy(Original, { construct(target, args) { (window as unknown as { audioStarts: number }).audioStarts++; return Reflect.construct(target, args) } })
  })
  let gone = false
  await page.route('**/api/answers/recent-answer', route => gone ? route.fulfill({ status: 404, json: {} }) : route.fulfill({ json: { id: 'recent-answer', request_text: 'Why compare groups?', text: 'Compare representation.', surface: 'playground', created_at: '2026-10-01T10:00:00Z', request: {}, metadata: {} } }))
  await page.goto('/answers/recent-answer')
  await expect(page.getByText('Compare representation.', { exact: true })).toBeVisible()
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('combobox', { name: 'Learning step', exact: true }).selectOption('2')
  await page.goto('/')
  const recent = page.locator('details').filter({ has: page.locator('summary', { hasText: 'Recently opened material' }) })
  await recent.locator('summary').click()
  await expect(recent.getByRole('link', { name: 'Why compare groups?' })).toHaveAttribute('href', '/answers/recent-answer')
  await recent.getByRole('link', { name: 'Harmonics' }).focus()
  await page.keyboard.press('Enter')
  const open = page.getByRole('button', { name: 'Open saved audio lesson', exact: true })
  await expect(open).toBeVisible()
  expect(await page.evaluate(() => (window as unknown as { audioStarts: number }).audioStarts)).toBe(0)
  await open.click()
  await expect(page.getByRole('combobox', { name: 'Learning step', exact: true })).toHaveValue('2')
  await page.goto('/')
  await page.reload()
  await recent.locator('summary').click()
  await page.screenshot({ path: info.outputPath('recent-answer-audio.png'), fullPage: true })
  gone = true
  await recent.getByRole('link', { name: 'Why compare groups?' }).click()
  await expect(page.getByText('This saved answer is unavailable.')).toBeVisible()
  expect(writes).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
