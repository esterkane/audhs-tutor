import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`calculated tutor reply fits the screen at ${width}px`, async ({ page }, info) => {
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
    await page.route('**/api/playground/tutor**', (route) => {
      modelRequests++
      return route.fulfill({ json: { text: "Local group-count calculation (exact fractions, not a grade):\n\n    Total: 150 before \u2192 120 after\n    Group \"A\": 100 before \u2192 90 after; 10 removed\n      Retained: 9/10\n      Representation: 2/3 \u2192 3/4\n      Share within entered groups: increased\n    Group \"B\": 50 before \u2192 30 after; 20 removed\n      Retained: 3/5\n      Representation: 1/3 \u2192 1/4\n      Share within entered groups: decreased\n\nComputed from user-entered counts, not verified dataset results. Assumes nonoverlapping groups, the same counting unit and unchanged membership, with rows removed rather than added. Representation is within the entered groups only. Counts do not establish causes, model accuracy, fairness or a grade. Undefined means a zero denominator.", turn_id: 'fixture', model: 'fixture', route: 'fake', source_note: 'Synthetic calculation' } })
    })
    await page.goto('/programs')
    await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
    await page.getByText('Compare group counts locally', { exact: true }).click()
    await page.getByLabel('Group 1 before count', { exact: true }).fill('100')
    await page.getByLabel('Group 1 after count', { exact: true }).fill('90')
    await page.getByLabel('Group 2 before count', { exact: true }).fill('50')
    await page.getByLabel('Group 2 after count', { exact: true }).fill('30')
    const compare = page.getByRole('button', { name: 'Compare counts', exact: true })
    await compare.focus()
    await page.keyboard.press('Enter')
    const table = page.getByRole('table')
    await expect(table).toContainText('90')
    await expect(table).toContainText('60')
    await expect(table).toContainText('10')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    expect(modelRequests).toBe(0)
    const attach = page.getByRole('button', { name: 'Attach counts to tutor', exact: true })
    await attach.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText(/Counts included in tutor messages until removed or edited/)).toContainText(
      'A: 100 → 90',
    )
    expect(modelRequests).toBe(0)
    await page.screenshot({ path: info.outputPath('count-attachment.png'), fullPage: true })
    const results = page.getByRole('region', { name: 'Group comparison results' })
    await results.screenshot({ path: info.outputPath('comparison-table.png') })
    if (width === 390) {
      await results.focus()
      await page.keyboard.press('ArrowRight')
      await expect.poll(() => results.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0)
    }
    await page.getByLabel('Your explanation').fill('Compare retained proportions')
    await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
    await expect(page.getByText(/Share within entered groups: increased/).last()).toBeVisible()
    await expect(page.getByText(/Share within entered groups: decreased/).last()).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    if (width === 390) {
      const calculation = page.getByLabel('Tutor response', { exact: true }).locator('pre')
      await expect(calculation).toHaveCount(1)
      await page.getByRole('button', { name: 'Check my answer', exact: true }).focus()
      let reached = false
      for (let step = 0; step < 30; step++) {
        await page.keyboard.press('Tab')
        if (await calculation.evaluate(el => el === document.activeElement)) {
          reached = true
          break
        }
      }
      expect(reached, 'Calculation is reachable with Tab').toBe(true)
      await page.keyboard.press('ArrowRight')
      await expect.poll(() => calculation.evaluate(el => el.scrollLeft)).toBeGreaterThan(0)
      await page.keyboard.press('Tab')
      await expect(calculation).not.toBeFocused()
    }
    await page.screenshot({ path: info.outputPath('count-direction.png'), fullPage: true })
  })
}
