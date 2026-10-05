import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`preferences sections preserve stored choices at ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preferences')
    for (const name of ['Learning and explanations', 'Session planning', 'Voice and recordings', 'Display and comfort']) {
      await expect(page.getByRole('heading', { name, exact: true, level: 2 })).toBeVisible()
    }
    const learning = page.getByRole('region', { name: 'Learning and explanations', exact: true })
    const example = learning.getByRole('button', { name: 'Worked example', exact: true })
    await example.focus()
    const saved = page.waitForResponse(response => response.url().endsWith('/api/preferences') && response.request().method() === 'PUT')
    await page.keyboard.press('Enter')
    const response = await saved
    expect(response.ok()).toBe(true)
    expect(response.request().postDataJSON()).toEqual({ key: 'tutor.representation_default', value: 'worked_example' })
    await expect(example).toHaveAttribute('aria-pressed', 'true')
    await page.reload()
    await expect(example).toHaveAttribute('aria-pressed', 'true')
    await expect(learning.getByRole('button', { name: 'No preferred format', exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Session planning', exact: true }).getByRole('button', { name: 'Low capacity', exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Display and comfort', exact: true }).getByRole('button', { name: 'Brown noise', exact: true })).toBeVisible()
    await learning.scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('learning-settings.png') })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  })
}

test('unrecognized editable preferences remain available without changing their values', async ({ page }) => {
  let enabled = false
  await page.route('**/api/preferences', async route => {
    if (route.request().method() === 'PUT') {
      expect(route.request().postDataJSON()).toEqual({ key: 'future.feature', value: true })
      enabled = true
    }
    await route.fulfill({ json: {
      values: { 'future.feature': enabled },
      specs: [{ key: 'future.feature', type: 'bool', default: false, description: 'Future preference' }],
    } })
  })
  await page.goto('/preferences')
  const extra = page.getByRole('region', { name: 'Additional preferences', exact: true })
  await extra.getByRole('button', { name: 'On', exact: true }).click()
  await expect(extra.getByRole('button', { name: 'On', exact: true })).toHaveAttribute('aria-pressed', 'true')
  expect(enabled).toBe(true)
})
