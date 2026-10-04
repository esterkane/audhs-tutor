import { expect, test } from '@playwright/test'
import { openMainMenu } from './helpers'

const hit = { chunk_id: 'passage-one', citation: 'Fixture source · section one', source_type: 'text', text: 'Compare representation before cleaning.', flagged: [], quarantined: false }
for (const width of [390, 1280]) {
  test(`Library source search and passage return ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const searches: unknown[] = [], writes: string[] = []
    page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/') && !request.url().endsWith('/api/corpus/search')) writes.push(request.url()) })
    await page.route('**/api/corpus/search', route => {
      searches.push(route.request().postDataJSON())
      return route.fulfill({ json: { hits: [hit] } })
    })
    await page.route('**/api/curriculum/chunks/passage-one', route => route.fulfill({ json: {
      ...hit, citation: hit.citation, document_title: 'Fixture source', trust_tier: 2,
      text: 'Full passage with surrounding context.', prev_text: 'Earlier paragraph.', next_text: 'Following paragraph.', uri: 'local/source.txt', open_url: null,
    } }))
    await page.goto('/sources')
    await expect(page.getByRole('heading', { name: 'Sources', exact: true })).toBeVisible()
    expect(searches).toEqual([])
    await openMainMenu(page)
    if (!(await page.getByRole('link', { name: 'Sources', exact: true }).isVisible())) await page.locator('summary').filter({ hasText: /^Library/ }).click()
    await expect(page.getByRole('link', { name: 'Sources', exact: true })).toBeVisible()
    const menu = page.getByRole('button', { name: /^Menu ·/ })
    if (await menu.isVisible()) await page.keyboard.press('Escape')
    await page.getByRole('searchbox', { name: 'Search source material' }).fill('representation')
    await page.getByRole('searchbox', { name: 'Search source material' }).press('Enter')
    const read = page.getByRole('button', { name: `Read passage: ${hit.citation}` })
    await expect(read).toBeVisible()
    expect(searches.length).toBeGreaterThan(0)
    for (const search of searches) expect(search).toEqual({ query: 'representation', k: 8, tutor_view: false })
    await read.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await expect(page.locator('[aria-label="Selected source passage"]')).toBeFocused()
    await expect(page).toHaveURL(/passage=passage-one/)
    await page.reload()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Close', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).not.toHaveURL(/passage=/)
    await expect(read).toBeFocused()
    await expect(page.getByRole('searchbox', { name: 'Search source material' })).toHaveValue('representation')
    await read.click()
    await page.getByRole('button', { name: 'Close', exact: true }).click()
    await expect(read).toBeFocused()
    await page.goBack()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await page.goForward()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('sources.png'), fullPage: true })
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(writes).toEqual([])
  })
}

test('search failure retry, empty results and deleted passage', async ({ page }) => {
  let failing = true
  await page.route('**/api/corpus/search', route => failing ? route.fulfill({ status: 503, json: {} }) : route.fulfill({ json: { hits: [] } }))
  await page.goto('/sources?q=missing&passage=gone')
  await expect(page.getByRole('button', { name: 'Retry source search' })).toBeVisible()
  failing = false
  await page.getByRole('button', { name: 'Retry source search' }).click()
  await expect(page.getByText(/No indexed passages matched/)).toBeVisible()
  await expect(page.getByText(/selected passage is no longer/)).toBeVisible()
  await page.getByRole('button', { name: 'Clear search' }).click()
  await expect(page.getByText('Enter a topic or phrase to find source material.')).toBeVisible()
})

test('late source search does not replace the new query', async ({ page }) => {
  let release!: () => void, finish!: () => void, start!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  const delivered = new Promise<void>(resolve => { finish = resolve })
  const started = new Promise<void>(resolve => { start = resolve })
  await page.route('**/api/corpus/search', async route => {
    const query = route.request().postDataJSON().query
    if (query === 'old') { start(); await pending }
    await route.fulfill({ json: { hits: [{ ...hit, citation: query }] } })
    if (query === 'old') finish()
  })
  await page.goto('/sources?q=old')
  await started
  await page.getByRole('searchbox', { name: 'Search source material' }).fill('new')
  await page.getByRole('button', { name: 'Search sources', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'new', exact: true })).toBeVisible()
  release()
  await delivered
  await expect(page.getByRole('heading', { name: 'old', exact: true })).toHaveCount(0)
})
