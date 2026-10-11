import { expect, test } from '@playwright/test'

const lesson = { document_id: 'recording-a', title: 'Example recording', course: null, section: null,
  lecture: null, language: 'en', sections: 3, done: 1, media_available: false, duration_s: 30, timed_chunks: 3 }
for (const width of [320, 1280]) test(`listening read recovery preserves work ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let failed = true
  await page.route('**/api/listening/lessons', route => route.fulfill(failed
    ? { status: 503, json: { error: { code: 'unavailable', message: 'Recording storage unavailable' } } }
    : { json: { lessons: [lesson] } }))
  await page.goto('/vocab')
  await expect(page.getByRole('alert').filter({ hasText: 'Could not load recordings.' })).toBeVisible()
  await expect(page.getByText('No timed transcripts in the corpus yet.', { exact: false })).toHaveCount(0)
  await page.locator('summary').filter({ hasText: /^Add one card$/ }).click()
  await page.getByLabel('Word', { exact: true }).fill('retained')
  failed = false
  await page.getByRole('button', { name: 'Retry recordings', exact: true }).focus()
  await page.keyboard.press('Enter')
  const select = page.getByLabel('Lesson for the language block')
  await expect(select).toBeEnabled()
  await expect(select.getByRole('option', { name: /Example recording/ })).toHaveCount(1)
  failed = true
  await page.getByRole('button', { name: 'Refresh recordings', exact: true }).click()
  await expect(page.getByRole('status').filter({ hasText: 'The last loaded list is kept.' })).toBeVisible()
  await expect(select.getByRole('option', { name: /Example recording/ })).toHaveCount(1)
  await expect(page.getByLabel('Word', { exact: true })).toHaveValue('retained')
  expect((await select.boundingBox())!.height).toBeGreaterThanOrEqual(44)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: info.outputPath('listening-recovery.png'), fullPage: true })
})

test('listening preference failure cannot overwrite an unknown choice', async ({ page }) => {
  let fail = true
  let writes = 0
  await page.route('**/api/listening/lessons', route => route.fulfill({ json: { lessons: [lesson] } }))
  await page.route('**/api/preferences', route => {
    if (route.request().method() === 'PUT') {
      writes++
      return route.fulfill({ json: { values: { 'listening.document_id': route.request().postDataJSON().value }, specs: [] } })
    }
    return route.fulfill(fail ? { status: 503, json: { error: { code: 'unavailable', message: 'Preferences unavailable' } } }
      : { json: { values: { 'listening.document_id': 'recording-a' }, specs: [] } })
  })
  await page.goto('/vocab')
  const select = page.getByLabel('Lesson for the language block')
  await expect(select).toBeDisabled()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not load your listening choice.' })).toBeVisible()
  expect(writes).toBe(0)
  fail = false
  await page.getByRole('button', { name: 'Retry listening choice' }).focus()
  await page.keyboard.press('Enter')
  await expect(select).toBeEnabled()
  await expect(select).toHaveValue('recording-a')
  await select.focus()
  await expect(select).toBeFocused()
  await select.selectOption('')
  await expect(page.getByRole('status').filter({ hasText: 'Listening choice saved.' })).toBeVisible()
  expect(writes).toBe(1)
})

 test('listening loading is distinct from a confirmed empty list', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/listening/lessons', async route => {
    await held
    await route.fulfill({ json: { lessons: [] } })
  })
  await page.goto('/vocab')
  await expect(page.getByRole('status').filter({ hasText: 'Loading recordings…' })).toBeVisible()
  await expect(page.getByText('No timed transcripts in the corpus yet.', { exact: false })).toHaveCount(0)
  release()
  await expect(page.getByText('No timed transcripts in the corpus yet.', { exact: false })).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: 'Loading recordings…' })).toHaveCount(0)
})
