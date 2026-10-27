import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [390, 1280]) test(`notebook requirements are read-only at ${width}`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 })
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: { title: 'Synthetic', courses: [{ id: 'check', title: 'Fixture course', project: 'Read', status: 'Fixture', sections: [] }] } }))
  await page.route('**/api/notebooks/status', route => route.fulfill({ json: { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready', url: null, course_id: '' } }))
  let checks = 0
  let starts = 0
  await page.route('**/api/notebooks/start', route => { starts++; return route.abort() })
  await page.route('**/api/notebooks/check?*', route => {
    expect(route.request().method()).toBe('GET')
    expect(new URL(route.request().url()).searchParams.get('course_id')).toBe('check')
    checks++
    return route.fulfill({ json: { status: 'checked', message: 'Static check only.', code_cells: 5,
      imports: ['json', 'missing_extra', 'winreg'], unavailable_imports: ['missing_extra', 'winreg'], unavailable_standard_imports: ['winreg'], local_imports: [], possible_exercise_cells: [3], unparsed_cells: [2], install_cells: [2] } })
  })
  await page.goto('/programs?course=check')
  await page.getByText('Full course notebook and files', { exact: true }).click()
  await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
  await page.getByText('Notebook requirements and exercise readiness', { exact: true }).click()
  const check = page.getByRole('button', { name: 'Check notebook requirements', exact: true })
  await expect(check).toBeEnabled()
  expect(checks).toBe(0)
  await check.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(/Imports not found in this environment: missing_extra/)).toBeVisible()
  await expect(page.getByText(/Standard-library modules unavailable in this Python build or platform: winreg/)).toBeVisible()
  await expect(page.getByText(/Imported modules were found in standard package locations/)).toHaveCount(0)
  await expect(page.getByText(/Possible unfinished exercise cells: 3/)).toBeVisible()
  await expect(page.getByText(/Installation commands appear in cells 2/)).toBeVisible()
  expect(checks).toBe(1)
  expect(starts).toBe(0)
  await page.addScriptTag({ content: axe.source })
  expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
