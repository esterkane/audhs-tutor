import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`group counts stay local and survive reload at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'fixture-session' } }))
    await page.route('**/local-learning/program.json', (route) =>
      route.fulfill({
        json: {
          title: 'Practice',
          courses: [
            {
              id: 'fixture',
              title: 'Data',
              project: 'Inspect',
              status: 'Fixture',
              sections: [
                {
                  id: 's',
                  title: 'Cleaning',
                  explanation: 'Compare representation before and after cleaning.',
                  example: 'Use your group counts.',
                  task: 'Compare',
                  question: 'What changes?',
                  hint: 'Compare rates.',
                  criteria: 'Explain the comparison.',
                  source: 'Synthetic fixture',
                },
              ],
            },
          ],
        },
      }),
    )
    let modelRequests = 0
    await page.route('**/api/playground/tutor', (route) => {
      modelRequests++
      return route.fulfill({ status: 500, json: { detail: 'No model should be called' } })
    })
    await page.goto('/programs')
    await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
    await page.getByText('Compare group counts locally', { exact: true }).click()
    await page.getByLabel('Group 1 before count', { exact: true }).fill('80')
    await page.getByLabel('Group 1 after count', { exact: true }).fill('72')
    await page.getByLabel('Group 2 before count', { exact: true }).fill('20')
    await page.getByLabel('Group 2 after count', { exact: true }).fill('8')
    const compare = page.getByRole('button', { name: 'Compare counts', exact: true })
    await compare.focus()
    await page.keyboard.press('Enter')
    const table = page.getByRole('table')
    await expect(table).toContainText('90')
    await expect(table).toContainText('40')
    await expect(table).toContainText('10')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    expect(modelRequests).toBe(0)
    await page.getByLabel('Group 2 after count', { exact: true }).fill('10')
    await expect(table).toHaveCount(0)
    await page.reload()
    await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
    await page.getByText('Compare group counts locally', { exact: true }).click()
    await expect(page.getByLabel('Group 2 after count', { exact: true })).toHaveValue('10')
    expect(modelRequests).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
