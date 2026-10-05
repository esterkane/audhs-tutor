import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) test(`search retains known matches after refresh failure ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let failing = false
  const reads: Record<string, number> = {}
  const fixtures: Record<string, unknown> = {
    '**/api/areas': { areas: [{ id: 'a', title: 'Example area', description: '', terms: [], courses: [], draft_ids: [], related: [] }], total_documents: 0, unassigned_documents: 0 },
    '**/api/skills': { skills: [{ id: 's', title: 'Example skill', description: '', unlocked: true, prerequisites: [], mastery: 0, state: {} }], next_skill_id: null },
    '**/local-learning/program.json': { title: 'Study', courses: [{ id: 'c', title: 'Example project', project: 'Practice', status: 'ready', sections: [{ id: 'x', title: 'Step', explanation: 'Example', task: 'Try', question: 'Why?', hint: 'Look', criteria: 'Explain', source: 'Local' }] }] },
    '**/api/answers?*': { items: [{ id: 'a', request_text: 'Example answer', preview: 'Evidence', created_at: '2026-10-01', surface: 'tutor' }], next_cursor: null },
    '**/api/corpus/search': { hits: [{ chunk_id: 'p', citation: 'Example source', source_type: 'text', text: 'Evidence', flagged: [], quarantined: false }] },
  }
  for (const [pattern, json] of Object.entries(fixtures)) await page.route(pattern, route => {
    reads[pattern] = (reads[pattern] ?? 0) + 1
    return route.fulfill(failing ? { status: 503, json: {} } : { json })
  })
  await page.route('**/api/curriculum/chunks/p', route => route.fulfill({ json: { chunk_id: 'p', citation: 'Example source', text: 'Full evidence', document_title: 'Example', source_type: 'text', trust_tier: 2, uri: 'example.txt', open_url: null } }))
  await page.goto('/search?q=example')
  const names = ['Example area', 'Example skill', 'Example project · Step', 'Example answer', 'Example source']
  for (const name of names) await expect(page.getByRole('link', { name, exact: true })).toBeVisible()
  await page.getByRole('link', { name: 'Example source', exact: true }).click()
  await expect(page.getByText('Full evidence', { exact: true })).toBeVisible()
  failing = true
  await page.goBack()
  await expect(page.getByRole('button', { name: 'Retry source search' })).toBeVisible()
  for (const name of names) await expect(page.getByRole('link', { name, exact: true })).toBeVisible()
  await expect(page.getByText('Showing previously loaded results; they may be out of date.', { exact: true })).toHaveCount(5)
  const counts = { ...reads }
  failing = false
  const retry = page.getByRole('button', { name: 'Retry source search' })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(retry).toHaveCount(0)
  for (const pattern of Object.keys(fixtures)) expect(reads[pattern]).toBe(counts[pattern] + (pattern === '**/api/corpus/search' ? 1 : 0))
  await page.getByRole('heading', { name: 'Indexed sources', exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('retained-search.png') })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
})
