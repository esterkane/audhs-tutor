import { expect, test } from '@playwright/test'

test('failed Home reminder action retains the thought and explains recovery', async ({ page }) => {
  await page.route('**/api/parking?status=parked', route => route.fulfill({ json: { items: [{ id: 'thought', text: 'Compare two examples', status: 'parked', node_id: null, created_at: 'now' }] } }))
  await page.route('**/api/parking/thought/actions', route => route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByText('Saved thoughts', { exact: true }).click()
  await page.getByRole('button', { name: /Promote to next session|Show on Home/ }).click()
  await expect(page.getByRole('alert').filter({ hasText: /Could not confirm/ })).toBeVisible()
  await expect(page.getByText('Compare two examples', { exact: true })).toBeVisible()
})

for (const width of [390, 1280]) {
  test(`thought actions show actual destination and allow keeping before removal ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let status = 'parked'
    let writes = 0
    let revision = 0
    const item = { id: 'thought', text: 'Compare two examples', node_id: null, created_at: 'now' }
    await page.route('**/api/parking?status=*', route => route.fulfill({ json: { items: new URL(route.request().url()).searchParams.get('status') === status ? [{ ...item, status, revision }] : [] } }))
    await page.route('**/api/parking/thought/*', async route => {
      writes++
      status = route.request().postDataJSON().action === 'promote' ? 'promoted' : 'dropped'
      revision++
      await route.fulfill({ json: { item: { ...item, status, revision, promoted_to: 'next_session' }, action_id: `action-${revision}`, action_revision: revision, can_undo: true } })
    })
    await page.goto('/')
    await page.getByRole('button', { name: 'Save for later', exact: true }).click()
    await page.getByText('Saved thoughts', { exact: true }).click()
    const dialog = page.getByRole('dialog')
    await dialog.getByRole('button', { name: 'Remove…', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(dialog.getByRole('button', { name: 'Keep thought', exact: true })).toBeFocused()
    await dialog.getByRole('button', { name: 'Keep thought' }).click()
    await expect(dialog.getByRole('button', { name: 'Remove…', exact: true })).toBeFocused()
    expect(writes).toBe(0)
    await dialog.getByRole('button', { name: 'Show on Home', exact: true }).click()
    await expect(dialog.getByRole('status').filter({ hasText: 'Shown on Home' })).toBeVisible()
    expect(writes).toBe(1)
    await page.keyboard.press('Escape')
    await expect(page.getByText('Thoughts to revisit', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Remove…', exact: true }).click()
    await expect(page.getByText(/After removal, Undo is available/)).toBeVisible()
    await page.screenshot({ path: info.outputPath('remove-confirmation.png'), fullPage: true })
    await page.getByRole('button', { name: 'Remove thought', exact: true }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Removed from reminders' })).toBeFocused()
    expect(writes).toBe(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}


test('stalled thought action becomes retryable without repeated or automatic submissions', async ({ page }) => {
  await page.clock.install()
  let posts = 0
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/parking?status=parked', route => route.fulfill({ json: { items: [{ id: 'thought', text: 'Wait for this idea', status: 'parked', node_id: null, created_at: 'now' }] } }))
  await page.route('**/api/parking/thought/actions', async route => {
    posts++
    await held
    await route.fulfill({ json: { item: { id: 'thought', text: 'Wait for this idea', status: 'promoted', revision: 1 }, action_id: 'a1', action_revision: 1, can_undo: true } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByText('Saved thoughts', { exact: true }).click()
  const action = page.getByRole('button', { name: 'Show on Home', exact: true })
  await action.focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')
  await expect(action).toBeDisabled()
  await expect.poll(() => posts).toBe(1)
  await page.clock.fastForward(16000)
  await expect(page.getByRole('button', { name: 'Retry same action' })).toBeEnabled()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not confirm' })).toBeVisible()
  release()
  expect(posts).toBe(1)
})
