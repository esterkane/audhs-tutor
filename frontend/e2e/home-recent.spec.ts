import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`Home returns to recently browsed areas without learning writes ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() => sessionStorage.setItem('audhs-browse-areas:v1', JSON.stringify({ version: 1, current: 'python', recent: ['python', 'gone', 'audio'] })))
    const writes: string[] = []
    const reviewReads: string[] = []
    page.on('request', request => {
      if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url())
      if (request.url().includes('/api/review/due')) reviewReads.push(request.url())
    })
    await page.route('**/api/areas', route => route.fulfill({ json: { areas: ['python', 'audio'].map(id => ({ id, title: id, terms: [], courses: [], documents: 0, related: [], description: '' })), total_documents: 0, unassigned_documents: 0 } }))
    await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'fixture', active_skill: { id: 'lesson', title: 'Comparing groups' }, due_reviews: 100, state: { skill_id: 'lesson', block_status: 'running', phase: 'teach', plan_complete: false } } }))
    await page.goto('/')
    const recent = page.getByRole('region', { name: 'Recently browsed areas' })
    await expect(recent.getByRole('link', { name: 'python', exact: true })).toBeVisible()
    await expect(recent.getByText(/previously visited area is unavailable/)).toBeVisible()
    await expect(page.getByText('At least 100 reviews are due for this saved session.')).toBeVisible()
    await expect(page.getByRole('button', { name: /Resume previous session: Comparing groups/ })).toBeVisible()
    await page.screenshot({ path: info.outputPath('home-recent.png'), fullPage: true })
    await recent.getByRole('link', { name: 'audio', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/areas\?area=audio$/)
    await page.goBack()
    await expect(recent.getByRole('link', { name: 'audio', exact: true })).toBeVisible()
    await page.reload()
    await expect(recent.getByRole('link', { name: 'audio', exact: true })).toBeVisible()
    expect(writes).toEqual([])
    expect(reviewReads).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('recent area lookup failure offers retry without inventing reviews or stale links', async ({ page }, info) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.addInitScript(() => sessionStorage.setItem('audhs-browse-areas:v1', JSON.stringify({ version: 1, current: 'python', recent: ['python'] })))
  let unavailable = true
  await page.route('**/api/areas', route => unavailable
    ? route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
    : route.fulfill({ json: { areas: [{ id: 'python', title: 'Understanding local inference and responsible machine learning applications', terms: [], courses: [], documents: 0, related: [], description: '' }] } }))
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  await page.goto('/')
  const recent = page.getByRole('region', { name: 'Recently browsed areas' })
  await expect(recent.getByRole('button', { name: 'Retry recent areas' })).toBeVisible()
  await expect(recent.getByRole('link', { name: 'python', exact: true })).toHaveCount(0)
  await expect(page.getByText(/reviews are due for this saved session/)).toHaveCount(0)
  unavailable = false
  await recent.getByRole('button', { name: 'Retry recent areas' }).click()
  await expect(recent.getByRole('link', { name: /Understanding local inference/ })).toBeVisible()
  await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('recent-long-title-zoom.png'), fullPage: true })
})
