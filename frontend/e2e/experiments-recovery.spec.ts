import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`experiment read recovery at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    let fail = true
    await page.route('**/api/experiments', route => route.fulfill({
      status: fail ? 503 : 200,
      json: fail ? { detail: 'Synthetic unavailable response' } : { experiments: [], templates: [], metrics: [] },
    }))
    await page.goto('/experiments')
    await expect(page.getByRole('alert').filter({ hasText: 'Could not load experiments.' })).toBeVisible()
    await expect(page.getByText('No experiments yet.', { exact: false })).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('read-error.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const retry = page.getByRole('button', { name: 'Retry loading experiments' })
    await retry.focus()
    await expect(retry).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(retry).toBeFocused()
    await expect(retry).toHaveAttribute('aria-disabled', 'false')
    fail = false
    await page.keyboard.press('Enter')
    await expect(page.getByText('No experiments yet.', { exact: false })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Experiments', exact: true })).toBeFocused()
    await expect(page.getByRole('alert').filter({ hasText: 'Could not load experiments.' })).toHaveCount(0)
  })
}

test('results retry keeps context and restores keyboard focus', async ({ page }) => {
  const experiment = { id: 'fixture', name: 'Read recovery fixture', status: 'done', unit_type: 'node', metric: 'delayed_recall', arms: [], hypothesis: 'Synthetic comparison' }
  await page.route('**/api/experiments', route => route.fulfill({ json: { experiments: [experiment], templates: [], metrics: [] } }))
  let fail = true
  await page.route('**/api/experiments/fixture/results', route => route.fulfill({
    status: fail ? 503 : 200,
    json: fail ? { detail: 'Unavailable' } : { experiment, analysis_version: 'fixture', outcome_window_days: 30, units_without_data: 0, low_fidelity_units: 0, caveats: [], metrics: [], units: [], primary_metric: 'delayed_recall' },
  }))
  await page.goto('/experiments')
  await page.getByRole('button', { name: 'Results', exact: true }).click()
  const retry = page.getByRole('button', { name: 'Retry loading results' })
  await expect(retry).toBeVisible()
  await retry.focus()
  fail = false
  await page.keyboard.press('Enter')
  await expect(page.getByText(/Analysis fixture/)).toBeVisible()
  await expect(page.getByRole('region', { name: 'Experiment results', exact: true })).toBeFocused()
})
