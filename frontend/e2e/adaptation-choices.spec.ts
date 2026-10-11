import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) test(`adaptation choices and undo remain explicit ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  const proposal = { id: 'design-proposal', what: 'Start with a worked example', why: 'Several recent attempts used hints.', pref: 'tutor.representation_default', value: 'worked_example', origin: 'observed_pattern', reversible: true }
  let selected = false
  let undone = false
  let undoCalls = 0
  const decisions: unknown[] = []
  await page.route('**/api/adaptations', route => route.fulfill({ json: { proposals: selected ? [] : [proposal] } }))
  await page.route('**/api/adaptations/log', route => route.fulfill({ json: { entries: selected ? [{ ...proposal, decision: 'default', trial: false, in_effect: !undone, undone_at: undone ? '2026-10-11T00:00:00Z' : null }] : [] } }))
  await page.route('**/api/adaptations/design-proposal/decide', async route => {
    decisions.push(route.request().postDataJSON())
    selected = true
    await route.fulfill({ json: { entries: [] } })
  })
  await page.route('**/api/adaptations/design-proposal/undo', async route => {
    undoCalls += 1
    if (undoCalls === 1) await route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Temporarily unavailable' } } })
    else { undone = true; await route.fulfill({ json: { entries: [] } }) }
  })
  await page.goto('/')
  await page.getByText('Optional learning adjustments (1)', { exact: true }).click()
  await expect(page.getByText('Several recent attempts used hints.', { exact: true })).toBeVisible()
  await expect(page.getByText('tutor.representation_default', { exact: true })).not.toBeVisible()
  const details = page.locator('summary').filter({ hasText: /^Technical details$/ })
  await details.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('tutor.representation_default', { exact: true })).toBeVisible()
  await page.keyboard.press('Enter')
  await page.getByRole('button', { name: 'Make this my default', exact: true }).focus()
  await page.keyboard.press('Enter')
  expect(decisions).toHaveLength(1)
  expect(decisions[0]).toMatchObject({ decision: 'default' })
  await page.goto('/preferences')
  await expect(page.getByText('Made default · in effect', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Undo', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Could not undo this adjustment' })).toBeVisible()
  await expect(page.getByText('Made default · in effect', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Undo', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Made default · undone', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Undo', exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
  await page.getByRole('heading', { name: 'Adaptation log', exact: true }).scrollIntoViewIfNeeded()
  await page.screenshot({ path: info.outputPath('adaptation-log.png') })
})
