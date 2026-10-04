import { openMainMenu } from './helpers'
import { expect, test } from '@playwright/test'

for (const width of [320, 390, 1280]) {
  test(`parking capture stays out of navigation ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: unknown[] = []
    await page.route('**/api/parking', async route => {
      if (route.request().method() === 'POST') {
        writes.push(route.request().postDataJSON())
        await route.fulfill({ status: 201, json: { id: 'fixture', text: 'Keep this thought', status: 'parked' } })
      } else await route.fulfill({ json: [] })
    })
    await page.goto('/curriculum')
    await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
    await openMainMenu(page)
    await page.getByText('Manage · Lesson drafts', { exact: true }).click()
    const park = page.getByRole('button', { name: 'Save for later' })
    const nav = page.getByRole('navigation', { name: 'Main navigation' })
    const triggerBox = await park.boundingBox()
    const navBox = await nav.boundingBox()
    expect(triggerBox!.y + triggerBox!.height).toBeLessThanOrEqual(navBox!.y)
    await park.focus()
    await page.keyboard.press('Enter')
    const input = page.getByRole('textbox', { name: 'Thought to save' })
    await expect(input).toBeFocused()
    await input.fill('Keep this thought')
    await page.keyboard.press('Escape')
    await expect(park).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(input).toHaveValue('Keep this thought')
    const dialog = page.getByRole('dialog')
    const box = await dialog.boundingBox()
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.y + box!.height).toBeLessThanOrEqual(900)
    await page.keyboard.press('Enter')
    await expect(dialog).toHaveCount(0)
    await expect(park).toBeFocused()
    await expect(page.getByRole('status').filter({ hasText: 'Thought saved.' })).toBeVisible()
    expect(writes).toHaveLength(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.screenshot({ path: info.outputPath('parked-header.png'), fullPage: true })
  })
}


test('save failure retains the draft and repeated submission sends only one pending request', async ({ page }, info) => {
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let posts = 0
  await page.route('**/api/parking', async route => {
    posts++
    if (posts === 1) {
      await pending
      await route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
    } else await route.fulfill({ status: 201, json: { id: 'saved', text: 'Keep my idea', status: 'parked' } })
  })
  await page.route('**/api/parking?status=parked', route => route.fulfill({ status: 503, json: { detail: 'Fixture list unavailable' } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  const input = page.getByRole('textbox', { name: 'Thought to save' })
  await input.fill('Keep my idea')
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await expect(input).toBeDisabled()
  expect(posts).toBe(1)
  release()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not confirm the save' })).toBeVisible()
  await expect(input).toHaveValue('Keep my idea')
  await expect(input).toBeEnabled()
  await page.getByText('Saved thoughts', { exact: true }).click()
  await expect(page.getByRole('button', { name: 'Retry saved thoughts' })).toBeVisible()
  await expect(page.getByText('No saved thoughts.', { exact: true })).toHaveCount(0)
  await page.screenshot({ path: info.outputPath('save-recovery.png'), fullPage: true })
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await expect(input).toHaveValue('Keep my idea')
  await page.getByRole('button', { name: 'Save thought', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(posts).toBe(2)
})


test('timed out save unlocks the draft and ignores a late response', async ({ page }) => {
  await page.clock.install()
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/parking', async route => {
    await held
    await route.fulfill({ status: 201, json: { id: 'late', text: 'Old idea', status: 'parked' } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  const input = page.getByRole('textbox', { name: 'Thought to save' })
  await input.fill('Old idea')
  await page.keyboard.press('Enter')
  await expect(page.getByRole('button', { name: 'Close', exact: true })).toBeVisible()
  await expect(page.getByText(/Closing does not cancel the save/)).toBeVisible()
  await page.clock.fastForward(16000)
  await expect(input).toBeEnabled()
  await expect(page.getByText(/Could not confirm the save/)).toBeVisible()
  await input.fill('Retain my edited idea')
  release()
  await expect(input).toHaveValue('Retain my edited idea')
  await expect(page.getByRole('dialog')).toBeVisible()
})

test('unsent thought survives reload without being submitted', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 })
  let posts = 0
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/api/parking')) posts++ })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByRole('textbox', { name: 'Thought to save' }).fill('Resume this thought after refresh')
  await page.reload()
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Thought to save' })).toHaveValue('Resume this thought after refresh')
  expect(posts).toBe(0)
  await page.screenshot({ path: info.outputPath('restored-draft.png'), fullPage: true })
})

test('restored unconfirmed draft uses its original context after the lesson changes', async ({ page }) => {
  await page.addInitScript(() => {
    sessionStorage.setItem('parking-draft:v1', JSON.stringify({ version: 1, draft: { text: 'Original thought', sessionId: 'original-session', skillId: 'original-skill', unconfirmed: true } }))
    localStorage.setItem('audhs-mode', JSON.stringify({ state: { mode: 'steady', energy: 3, sessionId: 'new-session', skillId: 'new-skill' }, version: 0 }))
  })
  const posts: unknown[] = []
  await page.route('**/api/parking', async route => {
    posts.push(route.request().postDataJSON())
    await route.fulfill({ status: 201, json: { id: 'confirmed', text: 'Original thought', status: 'parked' } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await expect(page.getByText(/An earlier save is unconfirmed/)).toBeVisible()
  await expect(page.getByText(/keeps its original session and skill context/)).toBeVisible()
  expect(posts).toHaveLength(0)
  await page.getByRole('button', { name: 'Save thought', exact: true }).click()
  await expect(page.getByRole('dialog')).toHaveCount(0)
  expect(posts).toEqual([{ session_id: 'original-session', node_id: 'original-skill', text: 'Original thought' }])
  expect(await page.evaluate(() => sessionStorage.getItem('parking-draft:v1'))).toBeNull()
})
