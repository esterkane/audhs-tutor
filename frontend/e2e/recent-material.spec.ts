import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`recent material restores source and workspace without learning writes ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let gone = false
    const writes: string[] = []
    page.on('request', r => { if (r.url().includes('/api/') && r.method() !== 'GET') writes.push(r.url()) })
    await page.route('**/api/curriculum/chunks/recent-source', route => gone ? route.fulfill({ status: 404, json: {} }) : route.fulfill({ json: { chunk_id: 'recent-source', citation: 'Source to revisit', document_title: 'Example', text: 'The original passage.', source_type: 'text', trust_tier: 2, uri: 'example.txt', open_url: null } }))
    await page.goto('/sources?chunk=recent-source')
    await expect(page.getByText('The original passage.')).toBeVisible()
    await page.goto('/playground?workspace=worked')
    await expect(page.locator('[data-capture-query="workspace=worked"]')).toBeVisible()
    await page.goto('/')
    const recent = page.locator('details').filter({ has: page.locator('summary', { hasText: 'Recently opened material' }) })
    await recent.locator('summary').click()
    await expect(recent.getByRole('link', { name: 'Source to revisit' })).toHaveAttribute('href', '/sources?chunk=recent-source')
    await expect(recent.getByRole('link', { name: '1. Read a worked example' })).toHaveAttribute('href', '/playground?workspace=worked')
    await page.screenshot({ path: info.outputPath('recent-material.png'), fullPage: true })
    await recent.getByRole('link', { name: '1. Read a worked example' }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/workspace=worked$/)
    await page.goBack()
    await page.reload()
    await recent.locator('summary').click()
    gone = true
    await recent.getByRole('link', { name: 'Source to revisit' }).click()
    await expect(page.getByText(/no longer in the corpus/)).toBeVisible()
    await page.goBack()
    if (!(await recent.getByRole('button', { name: 'Clear material history' }).isVisible())) await recent.locator('summary').click()
    await recent.getByRole('button', { name: 'Clear material history' }).click()
    await expect(recent).toHaveCount(0)
    await page.reload()
    await expect(recent).toHaveCount(0)
    expect(writes).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('missing workspace is not recorded as a successful fallback visit', async ({ page }) => {
  await page.goto('/playground?workspace=missing')
  await expect(page.getByText(/unavailable|not found|unknown/i).first()).toBeVisible()
  await page.goto('/')
  await expect(page.getByText('Recently opened material', { exact: true })).toHaveCount(0)
})
