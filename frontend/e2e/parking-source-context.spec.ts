import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`saved source bypasses retrieval and keeps draft ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let removed = false
    await page.route('**/api/corpus/search', route => route.fulfill({ status: 503, json: {} }))
    await page.route('**/api/curriculum/chunks/source-one', route => removed ? route.fulfill({ status: 404, json: {} }) : route.fulfill({ json: { chunk_id: 'source-one', citation: 'Example passage', document_title: 'Example', text: 'Read this exact passage.', source_type: 'text', trust_tier: 2, uri: 'source.txt', open_url: null } }))
    await page.goto('/sources?chunk=source-one')
    await expect(page.getByText('Read this exact passage.')).toBeVisible()
    const capture = page.getByRole('button', { name: 'Save a thought about this passage' })
    await capture.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('textbox', { name: 'Thought to save' }).fill(`Source reminder ${width}`)
    await page.getByRole('button', { name: 'Save thought', exact: true }).click()
    await page.getByRole('button', { name: 'Save for later', exact: true }).click()
    await page.getByText('Saved thoughts', { exact: true }).click()
    const link = page.getByRole('listitem').filter({ hasText: `Source reminder ${width}` }).getByRole('link', { name: 'Open original material: Example passage' })
    await expect(link).toHaveAttribute('href', '/sources?chunk=source-one')
    await link.focus()
    await page.keyboard.press('Enter')
    await page.reload()
    await expect(page.getByText('Read this exact passage.')).toBeVisible()
    await capture.click()
    await page.getByRole('textbox', { name: 'Thought to save' }).fill('Unfinished source thought')
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click()
    await expect(capture).toBeFocused()
    await capture.click()
    await expect(page.getByText(/Your unfinished thought and its original material are kept/)).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Thought to save' })).toHaveValue('Unfinished source thought')
    await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click()
    removed = true
    await page.reload()
    await expect(page.getByText(/This passage is no longer in the corpus/)).toBeVisible()
    await expect(capture).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('source-recovery.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
