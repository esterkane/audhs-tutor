import { expect, test } from '@playwright/test'
for (const width of [390, 1280]) test(`material search keeps independent results and query ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let sourceFail = true
  const requests: string[] = []
  await page.route('**/api/answers?*', route => { requests.push('answers'); return route.fulfill({ json: { items: [{ id: 'one', request_text: 'Explain groups', preview: 'Compare groups.', created_at: '2026-10-01', surface: 'tutor' }], next_cursor: null } }) })
  await page.route('**/api/corpus/search', route => { requests.push('sources'); return sourceFail ? route.fulfill({ status: 503, json: {} }) : route.fulfill({ json: { hits: [{ chunk_id: 'passage', citation: 'Example passage', source_type: 'text', text: 'Inspect the evidence.', flagged: ['warning'], quarantined: true }] } }) })
  await page.route('**/api/curriculum/chunks/passage', route => route.fulfill({ json: { chunk_id: 'passage', citation: 'Example passage', text: 'Full original evidence.', document_title: 'Example', source_type: 'text', trust_tier: 2, uri: 'example.txt', open_url: null } }))
  await page.goto('/search')
  expect(requests).toEqual([])
  await page.getByRole('searchbox', { name: 'Search phrase' }).fill('groups')
  expect(requests).toEqual([])
  await page.getByRole('searchbox', { name: 'Search phrase' }).press('Enter')
  await expect(page).toHaveURL(/q=groups$/)
  await expect(page.getByRole('link', { name: 'Explain groups' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry source search' })).toBeVisible()
  const answerCount = requests.filter(r => r === 'answers').length
  sourceFail = false
  await page.getByRole('button', { name: 'Retry source search' }).click()
  await expect(page.getByRole('link', { name: 'Example passage' })).toBeVisible()
  expect(requests.filter(r => r === 'answers')).toHaveLength(answerCount)
  await expect(page.getByText('Withheld from tutor context.')).toBeVisible()
  await page.screenshot({ path: info.outputPath('material-search.png'), fullPage: true })
  await page.getByRole('link', { name: 'Example passage' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Full original evidence.')).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('searchbox', { name: 'Search phrase' })).toHaveValue('groups')
  await page.reload()
  await expect(page.getByRole('link', { name: 'Explain groups' })).toBeVisible()
  await page.getByRole('button', { name: 'Clear search' }).click()
  await expect(page.getByText('Enter a phrase to search both collections.')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})

test('old searches cannot replace a new query and invalid queries send nothing', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  const seen: string[] = []
  await page.route('**/api/answers?*', async route => {
    const q = new URL(route.request().url()).searchParams.get('q')!
    seen.push(q)
    if (q === 'old') await held
    await route.fulfill({ json: { items: [{ id: q, request_text: `Answer ${q}`, preview: q }], next_cursor: null } }).catch(() => {})
  })
  await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [] } }))
  await page.goto(`/search?q=${'x'.repeat(201)}`)
  await expect(page.getByRole('alert')).toHaveText('Use a search of 200 characters or fewer.')
  expect(seen).toEqual([])
  await page.goto('/search?q=old')
  await expect(page.getByText('Searching saved explanations…')).toBeVisible()
  await page.getByRole('searchbox', { name: 'Search phrase' }).fill('new')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Answer new' })).toBeVisible()
  release()
  await expect(page.getByRole('link', { name: 'Answer old' })).toHaveCount(0)
})
