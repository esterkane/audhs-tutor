import { expect, test } from '@playwright/test'
for (const width of [390, 1280]) {
  test(`browse area is independent of learning ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: string[] = []
    page.on('request', r => { if (r.url().includes('/api/') && r.method() !== 'GET') writes.push(r.url()) })
    await page.route('**/api/areas', route => route.fulfill({ json: {
      areas: ['python', 'audio'].map(id => ({ id, title: id, terms: [], courses: [], documents: 0, related: [], description: '' })), total_documents: 0, unassigned_documents: 0,
    } }))
    await page.goto('/areas?area=python')
    await expect(page.getByText('Browse area · python', { exact: true })).toBeVisible()
    await page.getByRole('link', { name: 'Home', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Your next step' })).toBeVisible()
    await page.getByText('Browse area · python', { exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('link', { name: 'Open this area', exact: true }).click()
    await expect(page).toHaveURL(/areas\?area=python$/)
    await page.getByRole('combobox', { name: 'Area to browse' }).selectOption('audio')
    await expect(page).toHaveURL(/areas\?area=audio$/)
    await expect(page.getByRole('combobox', { name: 'Area to review' })).toHaveValue('audio')
    await page.reload()
    await expect(page.getByText('Browse area · audio', { exact: true })).toBeVisible()
    await page.getByText('Browse area · audio', { exact: true }).click()
    await expect(page.getByRole('combobox', { name: 'Area to browse' }).locator('optgroup[label="Recent in this tab"] option')).toHaveCount(2)
    expect(writes).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: info.outputPath('browse-area.png'), fullPage: true })
  })
}
