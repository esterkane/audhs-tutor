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

test('competing passages keep the explicitly selected source and unfinished draft', async ({ page }) => {
  await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [{ chunk_id: 'second', citation: 'Second passage', source_type: 'text', text: 'Second text', flagged: [], quarantined: false }] } }))
  await page.route('**/api/curriculum/chunks/*', route => {
    const first = route.request().url().endsWith('/first')
    return route.fulfill({ json: { chunk_id: first ? 'first' : 'second', citation: first ? 'First passage' : 'Second passage', document_title: 'Example', text: first ? 'First text' : 'Second text', source_type: 'text', trust_tier: 2, uri: 'source.txt', open_url: null } })
  })
  await page.goto('/sources?chunk=first&q=example&passage=second')
  const first = page.getByRole('region', { name: 'Saved source passage', exact: true }).getByRole('button', { name: 'Save a thought about this passage' })
  const second = page.locator('[aria-label="Selected source passage"]').getByRole('button', { name: 'Save a thought about this passage' })
  await expect(first).toBeVisible()
  await expect(second).toBeVisible()
  await first.click()
  await page.getByRole('textbox', { name: 'Thought to save' }).fill('Keep first source')
  await page.getByRole('dialog').getByRole('button', { name: 'Close', exact: true }).click()
  await second.click()
  await expect(page.getByText(/Your unfinished thought and its original material are kept/)).toBeVisible()
  await expect(page.getByRole('dialog').getByText(/Original material: First passage/)).toBeVisible()
  const saved = page.waitForRequest(request => request.method() === 'POST' && request.url().endsWith('/api/parking'))
  await page.getByRole('button', { name: 'Save thought', exact: true }).click()
  expect((await saved).postDataJSON().original_context.chunk_id).toBe('first')
  await expect(second).toBeFocused()
  await second.click()
  await page.getByRole('textbox', { name: 'Thought to save' }).fill('Now the second source')
  await expect(page.getByRole('dialog').getByText(/Original material: Second passage/)).toBeVisible()
})

test('slow passage lookup offers retry without claiming deletion', async ({ page }) => {
  let release!: () => void
  const stalled = new Promise<void>(resolve => { release = resolve })
  let recovering = false
  await page.route('**/api/curriculum/chunks/slow', async route => {
    if (!recovering) await stalled
    await route.fulfill({ json: { chunk_id: 'slow', citation: 'Recovered passage', document_title: 'Example', text: 'Recovered text', source_type: 'text', trust_tier: 2, uri: 'source.txt', open_url: null } }).catch(() => {})
  })
  await page.goto('/sources?chunk=slow')
  await expect(page.getByText('Loading passage…')).toBeVisible()
  await expect(page.getByText(/does not mean the source was removed/)).toBeVisible({ timeout: 20000 })
  recovering = true
  await page.getByRole('button', { name: 'Retry passage' }).click()
  await expect(page.getByText('Recovered text', { exact: true })).toBeVisible()
  release()
  await expect(page.getByText(/no longer in the corpus/)).toHaveCount(0)
})
