import { test, expect } from '@playwright/test'

for (const width of [390, 1280]) test(`unchanged thought retries retain identity after refresh ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  const requests: Record<string, unknown>[] = []
  await page.route('**/api/parking', async route => {
    requests.push(route.request().postDataJSON())
    if (requests.length === 1) await route.abort()
    else await route.fulfill({ status: 201, json: { id: 'same', status: 'dropped' } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByLabel('Thought to save').fill('Keep this idea')
  await page.getByRole('button', { name: 'Save thought', exact: true }).click()
  await expect(page.getByText(/Retrying this unchanged thought/)).toBeVisible()
  await page.reload()
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await expect(page.getByLabel('Thought to save')).toHaveValue('Keep this idea')
  expect(requests).toHaveLength(1)
  await page.screenshot({ path: info.outputPath('retry-restored.png'), fullPage: true })
  await page.getByRole('button', { name: 'Save thought', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(/Retrying did not restore it/)).toBeVisible()
  expect(requests).toHaveLength(2)
  expect(requests[1]).toEqual(requests[0])
  expect(requests[0].request_key).toEqual(expect.any(String))
})

test('editing an unconfirmed thought explicitly creates a different save', async ({ page }) => {
  const requests: Record<string, unknown>[] = []
  await page.route('**/api/parking', async route => {
    requests.push(route.request().postDataJSON())
    await route.abort()
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Save for later', exact: true }).click()
  await page.getByLabel('Thought to save').fill('First idea')
  await page.getByRole('button', { name: 'Save thought', exact: true }).click()
  await expect(page.getByText(/Retrying this unchanged thought/)).toBeVisible()
  await page.getByLabel('Thought to save').fill('Changed idea')
  await expect(page.getByText(/cannot be matched to it/)).toBeVisible()
  await page.getByRole('button', { name: 'Save as new thought', exact: true }).click()
  await expect(page.getByText(/Retrying this unchanged thought/)).toBeVisible()
  expect(requests).toHaveLength(2)
  expect(requests[1].request_key).not.toBe(requests[0].request_key)
  expect(requests[1].text).toBe('Changed idea')
})
