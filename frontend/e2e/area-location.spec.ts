import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`area browsing survives history and refresh ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: string[] = []
    page.on('request', request => {
      if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url())
    })
    await page.route('**/api/areas', route => route.fulfill({ json: {
      areas: ['python', 'audio'].map(id => ({ id, title: id === 'python' ? 'Python' : 'Audio', terms: [], courses: [], documents: 0, related: [], description: '' })),
      total_documents: 0, unassigned_documents: 0,
    } }))
    await page.goto('/areas')
    const select = page.getByRole('combobox', { name: 'Area to review' })
    await select.selectOption('python')
    await expect(page).toHaveURL(/area=python/)
    await select.selectOption('audio')
    await expect(page).toHaveURL(/area=audio/)
    await page.goBack()
    await expect(select).toHaveValue('python')
    await page.goForward()
    await expect(select).toHaveValue('audio')
    await page.reload()
    await expect(select).toHaveValue('audio')
    await expect(page.getByRole('heading', { name: 'Audio', exact: true })).toBeVisible()
    await select.selectOption('python')
    await page.getByText('Edit area name and matching terms', { exact: true }).click()
    await page.getByRole('textbox', { name: 'Area name', exact: true }).fill('Unfinished Python name')
    await page.goBack()
    await expect(page.getByRole('alert')).toContainText('Your edits are still open')
    await expect(page.getByRole('textbox', { name: 'Area name', exact: true })).toHaveValue('Unfinished Python name')
    await page.getByRole('button', { name: 'Save for later', exact: true }).click()
    await page.getByLabel('Thought to save').fill('Remember displayed area')
    const captured = await page.evaluate(() => JSON.parse(sessionStorage.getItem('parking-draft:v1')!).draft.originalContext)
    expect(captured.area_id).toBe('python')
    await page.getByRole('button', { name: 'Close', exact: true }).click()
    await page.getByRole('button', { name: 'Keep editing here', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/area=python/)
    await expect(page.getByRole('alert')).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('area-location.png'), fullPage: true })
    expect(writes).toEqual([])
  })
}
