import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Explore keeps learning separate from browsing ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.emulateMedia({ colorScheme: width === 1280 ? 'dark' : 'light' })
  const writes: string[] = []
  page.on('request', request => { if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url()) })
  await page.route('**/api/areas', route => route.fulfill({ json: { areas: [
    { id: 'ready', title: 'Programming', description: 'Understand how programs transform data.', active_lessons: 1 },
    { id: 'empty', title: 'New area', description: '', active_lessons: 0 },
  ], total_documents: 999, unassigned_documents: 99 } }))
  let fail = true
  await page.route('**/api/areas/*/concepts', route => fail ? route.fulfill({ status: 503, json: {} }) : route.fulfill({ json: {
    area_id: route.request().url().includes('/ready/') ? 'ready' : 'empty',
    concepts: route.request().url().includes('/ready/') ? [{ id: 'concept', title: 'Transform a list', description: 'Compare inputs and outputs.', success_criteria: ['Explain each transformation'] }] : [],
  } }))
  await page.goto('/explore')
  await expect(page.getByRole('heading', { name: 'Explore', exact: true })).toBeVisible()
  await expect(page.getByText(/999 imported/)).toHaveCount(0)
  const area = page.getByRole('link', { name: 'Programming', exact: true })
  await area.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('alert')).toContainText('Could not load concepts')
  fail = false
  await page.getByRole('button', { name: 'Retry concepts' }).click()
  await expect(page.getByRole('heading', { name: 'Transform a list' })).toBeVisible()
  await expect(page.getByText('Explain each transformation')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Choose this lesson' })).toHaveAttribute('href', '/?lesson=concept')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('explore.png'), fullPage: true })
  await page.goBack()
  await page.getByRole('link', { name: 'New area', exact: true }).click()
  await expect(page.getByText(/No activated lessons in this area/)).toBeVisible()
  await expect(page.getByRole('link', { name: 'Choose this lesson' })).toHaveCount(0)
  expect(writes).toEqual([])
})

test('choosing an Explore lesson keeps an existing session unchanged', async ({ page, request }) => {
  const { API, endOpenSession, expectOk } = await import('./helpers')
  await endOpenSession(request)
  try {
    const created = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(created)
    const session = await created.json()
    const skills = await (await request.get(`${API}/api/skills`)).json()
    const skill = skills.skills[0]
    await page.route('**/api/areas', route => route.fulfill({ json: { areas: [{ id: 'sample', title: 'Sample area', description: '', active_lessons: 1 }], total_documents: 0, unassigned_documents: 0 } }))
    await page.route('**/api/areas/sample/concepts', route => route.fulfill({ json: { area_id: 'sample', concepts: [{ id: skill.id, title: skill.title, description: skill.description, success_criteria: skill.success_criteria }] } }))
    const writes: string[] = []
    page.on('request', r => { if (r.url().includes('/api/') && r.method() !== 'GET') writes.push(r.url()) })
    await page.goto('/explore?area=sample')
    await page.getByRole('link', { name: 'Choose this lesson', exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`lesson=${skill.id}`))
    await expect(page.getByRole('heading', { name: skill.title, exact: true })).toBeVisible()
    const current = await (await request.get(`${API}/api/sessions/current`)).json()
    expect(current.id).toBe(session.id)
    expect(writes).toEqual([])
  } finally { await endOpenSession(request) }
})
