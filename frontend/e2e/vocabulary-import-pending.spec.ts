import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`CSV preview and confirmation retain their settings ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let releaseImport!: () => void
  const heldImport = new Promise<void>(resolve => { releaseImport = resolve })
  let previews = 0
  let imports = 0
  await page.route('**/api/vocab/import/preview', async route => {
    previews++
    expect(route.request().postDataJSON()).toMatchObject({ lang: 'de', reverse: false })
    await held
    await route.fulfill({ json: { lang: 'de', rows: [{ row: 1, word: 'Haus', translation: 'house', example: null, status: 'new', problem: null }], columns: { word: 0, translation: 1 }, delimiter: ';', header: false, counts: { new: 1 }, errors: [] } })
  })
  await page.route('**/api/vocab/import', async route => {
    imports++
    expect(route.request().postDataJSON()).toMatchObject({ lang: 'de', reverse: false, source: null, rows: [{ word: 'Haus', translation: 'house', example: null }] })
    await heldImport
    return route.fulfill({ json: { lang: 'de', added: 1, reverse_added: 0, skipped_existing: 0, invalid: 0 } })
  })
  await page.goto('/vocab')
  const section = page.locator('details').filter({ has: page.locator('summary').filter({ hasText: /^Import a CSV list$/ }) })
  await section.locator('summary').first().click()
  await section.locator('summary').filter({ hasText: /^Or paste the list$/ }).click()
  await section.getByLabel('CSV text').fill('Haus;house')
  const preview = section.getByRole('button', { name: 'Preview', exact: true })
  await preview.evaluate(el => { (el as HTMLButtonElement).click(); (el as HTMLButtonElement).click() })
  await expect.poll(() => previews).toBe(1)
  await expect(section.getByLabel('Language', { exact: true })).toBeDisabled()
  await expect(section.getByLabel('Also create reverse cards', { exact: false })).toBeDisabled()
  await expect(section.getByLabel('CSV file', { exact: true })).toBeDisabled()
  release()
  const confirm = section.getByRole('button', { name: 'Import 1 card', exact: true })
  await confirm.focus()
  await page.keyboard.press('Enter')
  await expect(section.getByLabel('Word, row 1')).toBeDisabled()
  await expect(section.getByRole('button', { name: 'Start over (change language or direction)' })).toBeDisabled()
  releaseImport()
  await expect(section.getByRole('status').filter({ hasText: 'Imported 1 new card;' })).toBeVisible()
  expect(imports).toBe(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  const table = section.getByRole('region', { name: 'CSV preview rows; scroll horizontally for all columns' })
  await table.focus()
  if (width === 320) {
    await page.keyboard.press('ArrowRight')
    await expect.poll(() => table.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
    await table.evaluate(el => { el.scrollLeft = 0 })
  }
  await page.screenshot({ path: info.outputPath('import.png'), fullPage: true })
  await section.getByLabel('Word, row 1').fill('Baum')
  await expect(section.getByRole('status').filter({ hasText: 'Imported 1 new card;' })).toHaveCount(0)
})
