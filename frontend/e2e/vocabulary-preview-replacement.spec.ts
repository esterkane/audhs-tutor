import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`failed replacement keeps reviewed CSV edits ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  let previews = 0
  let imports = 0
  await page.route('**/api/vocab/import/preview', route => {
    previews++
    return previews === 1 ? route.fulfill({ json: {
      lang: 'de', rows: [{ row: 1, word: 'Haus', translation: 'house', example: null, status: 'new', problem: null }],
      columns: { word: 0, translation: 1 }, delimiter: ';', header: false, counts: { new: 1 }, errors: [],
    } }) : route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Preview unavailable' } } })
  })
  await page.route('**/api/vocab/import', route => {
    imports++
    expect(route.request().postDataJSON()).toMatchObject({ source: 'original.csv', rows: [{ word: 'Haus', translation: 'home', example: null }] })
    return route.fulfill({ json: { lang: 'de', added: 1, reverse_added: 0, skipped_existing: 0, invalid: 0 } })
  })
  await page.goto('/vocab')
  const section = page.locator('details').filter({ has: page.locator('summary').filter({ hasText: /^Import a CSV list$/ }) })
  await section.locator('summary').first().click()
  await section.getByLabel('CSV file', { exact: true }).setInputFiles({ name: 'original.csv', mimeType: 'text/csv', buffer: Buffer.from('Haus;house') })
  await section.getByLabel('Translation, row 1').fill('home')
  await section.getByLabel('CSV file', { exact: true }).setInputFiles({ name: 'replacement.csv', mimeType: 'text/csv', buffer: Buffer.from('Baum;tree') })
  await expect(section.getByRole('alert')).toContainText('Preview unavailable')
  await expect(section.getByLabel('Translation, row 1')).toHaveValue('home')
  const confirm = section.getByRole('button', { name: 'Import 1 card', exact: true })
  await confirm.focus()
  await page.keyboard.press('Enter')
  await expect.poll(() => imports).toBe(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: `/tmp/csv-preview-replacement-${width}.png`, fullPage: true })
})
