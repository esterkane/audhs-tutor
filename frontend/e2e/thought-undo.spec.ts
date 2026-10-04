import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`real reminder removal and promotion undo ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const text = `Undo example ${width}`
    const saved = await page.request.post('/api/parking', { data: { text } })
    expect(saved.ok()).toBe(true)
    await page.goto('/')
    await page.getByRole('button', { name: 'Save for later', exact: true }).click()
    await page.getByText('Saved thoughts', { exact: true }).click()
    const row = page.getByRole('listitem').filter({ hasText: text })
    await row.getByRole('button', { name: 'Remove…', exact: true }).click()
    await row.getByRole('button', { name: 'Remove thought', exact: true }).click()
    await expect(row).toHaveCount(0)
    const undo = page.getByRole('button', { name: 'Undo last change', exact: true })
    await undo.focus()
    await page.keyboard.press('Enter')
    await expect(row).toBeVisible()
    await expect(undo).toHaveCount(0)
    await row.getByRole('button', { name: 'Show on Home' }).click()
    await expect(row).toHaveCount(0)
    await undo.click()
    await expect(row).toBeVisible()
    await page.screenshot({ path: info.outputPath('undo-result.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('stale undo cannot replace a newer action', async ({ page }) => {
  const saved = (await page.request.post('/api/parking', { data: { text: 'Stale undo example' } })).json()
  const item = await saved
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByText('Saved thoughts', { exact: true }).click()
  await page.getByRole('listitem').filter({ hasText: 'Stale undo example' }).getByRole('button', { name: 'Show on Home' }).click()
  await expect(page.getByRole('button', { name: 'Undo last change' })).toBeVisible()
  await page.request.post(`/api/parking/${item.id}/drop`)
  await page.getByRole('button', { name: 'Undo last change' }).click()
  await expect(page.getByRole('alert').filter({ hasText: /This thought changed/ })).toBeVisible()
  const removed = await page.request.get('/api/parking?status=dropped')
  expect((await removed.json()).items.some((p: { id: string }) => p.id === item.id)).toBe(true)
})

test('lost action response retries the same receipt without another revision', async ({ page }) => {
  const item = await (await page.request.post('/api/parking', { data: { text: 'Lost response example' } })).json()
  const bodies: Record<string, unknown>[] = []
  await page.route(`**/api/parking/${item.id}/actions`, async route => {
    bodies.push(route.request().postDataJSON())
    const response = await route.fetch()
    if (bodies.length === 1) await route.abort('failed')
    else await route.fulfill({ response })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByText('Saved thoughts', { exact: true }).click()
  await page.getByRole('listitem').filter({ hasText: item.text }).getByRole('button', { name: 'Show on Home' }).click()
  await expect(page.getByRole('button', { name: 'Retry same action' })).toBeVisible()
  await page.getByRole('button', { name: 'Retry same action' }).click()
  await expect(page.getByRole('button', { name: 'Undo last change' })).toBeVisible()
  expect(bodies).toHaveLength(2)
  expect(bodies[0]).toEqual(bodies[1])
  const rows = await (await page.request.get('/api/parking?status=promoted')).json()
  expect(rows.items.find((p: { id: string }) => p.id === item.id).revision).toBe(1)
})
