import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Progress distinguishes records from independence ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  const writes: string[] = []
  page.on('request', request => { if (request.url().includes('/api/') && request.method() === 'POST') writes.push(request.url()) })
  const skill = (id: string) => ({ id, slug: id, title: `Concept ${id}`, description: '', domain: 'test', prerequisites: [], success_criteria: [], mastery: 0.9, unlocked: true, state: {} })
  await page.route('**/api/skills', route => route.fulfill({ json: { skills: [skill('a'), skill('b')], next_skill_id: 'a' } }))
  let failOlder = true
  await page.route('**/api/skills/*/evidence?*', route => {
    const url = new URL(route.request().url())
    const empty = url.pathname.includes('/b/')
    const offset = Number(url.searchParams.get('offset'))
    if (offset && failOlder) return route.fulfill({ status: 503, json: {} })
    return route.fulfill({ json: { skill_id: empty ? 'b' : 'a', offset, limit: 20, total: empty ? 0 : 21,
      dimensions: empty ? [] : [{ dimension: 'transfer', count: 21, last_recorded_at: '2026-01-02T00:00:00Z' }],
      items: empty ? [] : Array.from({ length: offset ? 1 : 20 }, (_, i) => ({ id: String(offset + i), dimension: 'transfer', recorded_at: '2026-01-02T00:00:00Z', score: 1, weight: 1, grader_level: 'local', attempt_id: 'attempt', answer_id: i === 0 ? 'saved-check' : null, reported_hint_count: 0, independence: 'not_verified' })),
    } })
  })
  await page.route('**/api/answers/saved-check', route => route.fulfill({ json: {
    id: 'saved-check', surface: 'assessment', created_at: '2026-01-02T00:00:00Z',
    request_text: 'Saved comparison question', request: { learner_answer: 'My recorded reasoning' },
    text: 'Saved comparison feedback', metadata: {},
  } }))
  await page.goto('/progress?skill=a')
  await expect(page.getByRole('heading', { name: 'Progress', exact: true })).toBeVisible()
  await expect(page.getByText(/^Not verified as independent work\./)).toBeVisible()
  await expect(page.getByText('Not yet checked.', { exact: true })).toHaveCount(3)
  const disclosure = page.locator('summary').filter({ hasText: 'Why does the tutor think this?' })
  await disclosure.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Reported hints: 0.', { exact: false })).toHaveCount(20)
  const savedLink = page.getByRole('link', { name: 'Open saved assessment', exact: true })
  await expect(savedLink).toHaveAttribute('href', '/answers/saved-check')
  await savedLink.focus()
  await expect(savedLink).toBeFocused()
  await expect(page.getByText('Saved question and feedback unavailable.', { exact: true })).toHaveCount(19)
  await page.getByRole('button', { name: 'Older records' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert')).toContainText('Showing the last loaded records')
  await expect(page.getByText('Records 1–20 of 21, newest first.')).toBeVisible()
  failOlder = false
  await page.getByRole('button', { name: 'Retry evidence' }).click()
  await expect(page.getByText('Records 21–21 of 21, newest first.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Newer records' })).toBeVisible()
  await page.screenshot({ path: info.outputPath('progress.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(writes).toEqual([])
  await savedLink.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/answers\/saved-check$/)
  await expect(page.getByText('Saved comparison feedback', { exact: true })).toBeVisible()
  await page.goBack()
  await expect(page).toHaveURL(/progress\?skill=a$/)
  await expect(page.getByRole('heading', { name: 'Concept a', exact: true })).toBeVisible()
  await page.getByLabel('Concept', { exact: true }).selectOption('b')
  await expect(page).toHaveURL(/skill=b$/)
  await expect(page.getByText('Not yet checked.', { exact: true })).toHaveCount(3)
  await disclosure.click()
  await expect(page.getByText('No assessment evidence recorded yet.')).toBeVisible()
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Concept a', exact: true })).toBeVisible()
})
