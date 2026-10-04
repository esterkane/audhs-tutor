import { expect, test } from '@playwright/test'

const areas = ['Python', 'Music', 'Empty'].map(title => ({ id: title.toLowerCase(), title, slug: title.toLowerCase(), terms: [], courses: [], documents: 0, draft_ids: [], active_lessons: 0, related: [] }))
const node = (id: string, outside = false) => ({ id, title: id, mastery: 0.2, unlocked: true, is_next: false, outside_area: outside, memory: { items: 0, due: 0 } })
const result = (area: string) => ({
  area_id: area || null, area_title: areas.find(a => a.id === area)?.title ?? null,
  nodes: area === 'empty' ? [] : area === 'music' ? [node('Harmonics')] : [node('Python concept'), node('Foundation', !!area)],
  edges: area === 'empty' || area === 'music' ? [] : [{ from: 'Foundation', to: 'Python concept', kind: 'prerequisite' }],
  mermaid: area === 'empty' ? 'graph LR' : area === 'music' ? 'graph LR\n a[Harmonics]' : 'graph LR\n a[Foundation] --> b[Python concept]',
})
for (const width of [390, 1280]) {
  test(`area map navigation retains explicit scope ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: string[] = []
    page.on('request', req => { if (req.url().includes('/api/') && req.method() !== 'GET') writes.push(req.url()) })
    await page.route('**/api/areas', route => route.fulfill({ json: { areas } }))
    await page.route('**/api/skills/map**', route => route.fulfill({ json: result(new URL(route.request().url()).searchParams.get('area_id') ?? '') }))
    await page.goto('/map?area=python')
    await expect(page.getByText('Prerequisite from outside this area', { exact: true })).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Map area' }).getByRole('option', { name: 'Music', exact: true })).toHaveCount(1)
    await expect(page.locator('main svg')).toBeVisible()
    await expect(page.locator('main svg')).toContainText('Foundation')
    await expect(page.getByText('Prerequisites: Foundation', { exact: true })).toBeVisible()
    await page.screenshot({ path: info.outputPath('scoped-map.png'), fullPage: true })
    await page.getByRole('combobox', { name: 'Map area' }).focus()
    await expect(page.getByRole('combobox', { name: 'Map area' })).toBeFocused()
    await page.getByRole('combobox', { name: 'Map area' }).selectOption('music')
    await expect(page).toHaveURL(/area=music$/)
    await expect(page.getByRole('listitem').filter({ hasText: 'Harmonics' })).toBeVisible()
    await expect(page.getByRole('listitem').filter({ hasText: 'Python concept' })).toHaveCount(0)
    await page.reload()
    await expect(page.getByRole('combobox', { name: 'Map area' })).toHaveValue('music')
    await page.goBack()
    await expect(page.getByRole('listitem').filter({ hasText: 'Python concept' })).toBeVisible()
    await page.goForward()
    await expect(page.getByRole('listitem').filter({ hasText: 'Harmonics' })).toBeVisible()
    await page.getByRole('combobox', { name: 'Map area' }).selectOption('empty')
    await expect(page.getByRole('status').filter({ hasText: 'No skills' })).toBeVisible()
    await page.getByRole('link', { name: 'Show all areas' }).click()
    await expect(page).toHaveURL(/\/map$/)
    await expect(page.getByRole('listitem').filter({ hasText: 'Python concept' })).toBeVisible()
    await expect(page.getByText('Prerequisite from outside this area', { exact: true })).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('area-map.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(writes).toEqual([])
    await page.getByRole('button', { name: 'Learn this', exact: true }).first().focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/lesson=Python\+concept|lesson=Python%20concept/)
  })
}

test('unavailable scope and failed catalog retain global recovery', async ({ page }) => {
  await page.route('**/api/areas', route => route.fulfill({ status: 503, json: {} }))
  await page.route('**/api/skills/map**', route => new URL(route.request().url()).searchParams.has('area_id')
    ? route.fulfill({ status: 404, json: { detail: 'Area unavailable' } })
    : route.fulfill({ json: result('') }))
  await page.goto('/map?area=missing')
  await expect(page.getByText('Could not load this area map. The area may be unavailable.', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Retry areas' })).toBeVisible()
  await page.getByRole('link', { name: 'Show all areas' }).click()
  await expect(page.getByRole('listitem').filter({ hasText: 'Python concept' })).toBeVisible()
})

test('late scope response cannot replace the current map', async ({ page }) => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let started!: () => void
  const seen = new Promise<void>(resolve => { started = resolve })
  let finished!: () => void
  const delivered = new Promise<void>(resolve => { finished = resolve })
  await page.route('**/api/areas', route => route.fulfill({ json: { areas } }))
  await page.route('**/api/skills/map**', async route => {
    const area = new URL(route.request().url()).searchParams.get('area_id') ?? ''
    if (area === 'python') { started(); await pending }
    await route.fulfill({ json: result(area) })
    if (area === 'python') finished()
  })
  await page.goto('/map?area=python')
  await seen
  await page.getByRole('combobox', { name: 'Map area' }).selectOption('music')
  await expect(page.getByRole('listitem').filter({ hasText: 'Harmonics' })).toBeVisible()
  release()
  await delivered
  await expect(page.getByRole('combobox', { name: 'Map area' })).toHaveValue('music')
  await expect(page.getByRole('listitem').filter({ hasText: 'Python concept' })).toHaveCount(0)
})
