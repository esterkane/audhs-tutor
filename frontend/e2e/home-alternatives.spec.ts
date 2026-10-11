import { expect, test } from '@playwright/test'

const session = { id: 'saved', mode: 'steady', energy: 3, active_skill: { id: 'original', title: 'Original concept' }, state: { skill_id: 'original', block_status: 'running', block_index: 0, phase: 'teach', plan_complete: false, block: { type: 'new_material' } }, plan: [{ type: 'new_material', planned_min: 20 }], due_reviews: 0 }

for (const width of [320, 1280]) test(`Home alternatives preserve a saved lesson ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.route('**/api/sessions/current', route => route.fulfill({ json: session }))
  await page.route('**/api/sessions/saved', route => route.fulfill({ json: session }))
  await page.route('**/api/review/due?*', route => route.fulfill({ json: { items: [], total_due: 0 } }))
  const writes: string[] = []
  page.on('request', r => { if (r.url().includes('/api/') && r.method() !== 'GET') writes.push(r.url()) })
  await page.goto('/')
  const choices = page.getByRole('region', { name: 'Other ways to learn' })
  await expect(choices.getByRole('link', { name: 'Learn something else' })).toHaveAttribute('href', '/map')
  await expect(choices.getByRole('link', { name: 'Explore', exact: true })).toHaveAttribute('href', '/explore')
  const explore = choices.getByRole('link', { name: 'Explore', exact: true })
  await explore.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Explore', exact: true })).toBeVisible()
  await page.goBack()
  await expect(page.getByText('Original concept', { exact: true })).toBeVisible()
  expect(writes).toEqual([])
  const quick = choices.getByRole('button', { name: 'Quick review' })
  await expect(quick).toBeEnabled()
  await quick.focus()
  await page.screenshot({ path: info.outputPath('home-alternatives.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/review$/)
  await expect(page.getByText('Nothing is due right now.')).toBeVisible()
  expect(writes).toEqual([])
  await page.getByRole('button', { name: 'Back to the session' }).click()
  await expect(page).toHaveURL(/\/session$/)
  expect(writes).toEqual([])
})

test('Quick review starts once when no saved session exists', async ({ page }) => {
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  let starts = 0
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/sessions', async route => {
    starts++
    await held
    await route.fulfill({ status: 201, json: session })
  })
  await page.route('**/api/sessions/saved', route => route.fulfill({ json: session }))
  await page.route('**/api/review/due?*', route => route.fulfill({ json: { items: [], total_due: 0 } }))
  await page.goto('/')
  const quick = page.getByRole('button', { name: 'Quick review' })
  await expect(quick).toBeEnabled()
  await quick.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Opening review…' })).toBeDisabled()
  await expect.poll(() => starts).toBe(1)
  release()
  await expect(page).toHaveURL(/\/review$/)
  expect(starts).toBe(1)
})

test('failed fresh session lookup does not start another session and can retry', async ({ page }) => {
  let fail = false
  let starts = 0
  await page.route('**/api/sessions/current', route => fail ? route.fulfill({ status: 503, json: { detail: 'Try again' } }) : route.fulfill({ json: session }))
  await page.route('**/api/sessions', route => { starts++; return route.abort() })
  await page.route('**/api/sessions/saved', route => route.fulfill({ json: session }))
  await page.route('**/api/review/due?*', route => route.fulfill({ json: { items: [], total_due: 0 } }))
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Continue', exact: true })).toBeVisible()
  fail = true
  await page.getByRole('button', { name: 'Quick review' }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not open quick review' })).toBeVisible()
  expect(starts).toBe(0)
  fail = false
  await page.getByRole('button', { name: 'Quick review' }).click()
  await expect(page).toHaveURL(/\/review$/)
  expect(starts).toBe(0)
})

test('leaving during session creation cannot redirect the learner back', async ({ page }) => {
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let started = false
  await page.route('**/api/sessions', async route => { started = true; await held; await route.fulfill({ status: 201, json: session }) })
  await page.goto('/')
  await page.getByRole('button', { name: 'Quick review' }).click()
  await expect.poll(() => started).toBe(true)
  await page.getByRole('region', { name: 'Other ways to learn' }).getByRole('link', { name: 'Explore', exact: true }).click()
  const response = page.waitForResponse(r => r.url().endsWith('/api/sessions') && r.request().method() === 'POST')
  release()
  await response
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))))
  await expect(page).toHaveURL(/\/explore$/)
  await expect(page.getByRole('heading', { name: 'Explore', exact: true })).toBeVisible()
})

test('a stalled lookup times out and unlocks Quick review for retry', async ({ page }) => {
  await page.clock.install()
  let hold = false
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/sessions/current', async route => { if (hold) await held; await route.fulfill({ json: session }) })
  await page.route('**/api/sessions/saved', route => route.fulfill({ json: session }))
  await page.route('**/api/review/due?*', route => route.fulfill({ json: { items: [], total_due: 0 } }))
  await page.goto('/')
  const quick = page.getByRole('button', { name: 'Quick review' })
  await expect(quick).toBeEnabled()
  hold = true
  await quick.click()
  await page.clock.fastForward(16000)
  await expect(page.getByRole('alert').filter({ hasText: 'loading took too long' })).toBeVisible()
  await expect(quick).toBeEnabled()
  hold = false
  release()
  await quick.click()
  await expect(page).toHaveURL(/\/review$/)
})

test('Quick review waits for session preferences before creating a session', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  await page.route('**/api/preferences', async route => { await held; await route.fulfill({ json: { values: {}, specs: [] } }) })
  await page.goto('/')
  const quick = page.getByRole('button', { name: 'Quick review' })
  await expect(quick).toBeDisabled()
  release()
  await expect(quick).toBeEnabled()
})


test('Back during a pending session start keeps Home selected', async ({ page }) => {
  await page.route('**/api/sessions/current', route => route.fulfill({ json: null }))
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  let started = false
  await page.route('**/api/sessions', async route => {
    started = true
    await held
    await route.fulfill({ status: 201, json: session })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Quick review' }).click()
  await expect.poll(() => started).toBe(true)
  await page.getByRole('region', { name: 'Other ways to learn' }).getByRole('link', { name: 'Explore', exact: true }).click()
  await page.goBack()
  await expect(page).toHaveURL(/\/$/)
  const response = page.waitForResponse(r => r.url().endsWith('/api/sessions') && r.request().method() === 'POST')
  release()
  await response
  await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))))
  await expect(page).toHaveURL(/\/$/)
  await expect(page.getByRole('heading', { name: 'Home', exact: true })).toBeVisible()
})
