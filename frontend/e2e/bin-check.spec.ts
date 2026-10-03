import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`explicit local notebook boundary check at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'fixture-session' } }))
    await page.route('**/local-learning/program.json', (route) =>
      route.fulfill({
        json: {
          title: 'Practice',
          courses: [
            {
              id: 'fixture',
              title: 'Boundaries',
              project: 'Inspect',
              status: 'Fixture',
              sections: [],
              notebook: '/local-learning/bins.ipynb',
            },
          ],
        },
      }),
    )
    await page.route('**/local-learning/bins.ipynb', (route) =>
      route.fulfill({
        json: {
          nbformat: 4,
          nbformat_minor: 5,
          metadata: {},
          cells: [
            {
              cell_type: 'code',
              source: 'pd.cut(ages, [0,18,65])',
              metadata: {},
              outputs: [],
              execution_count: null,
            },
          ],
        },
      }),
    )
    let calls = 0
    await page.route('**/api/playground/tutor', async (route) => {
      calls++
      expect(route.request().postDataJSON()).toMatchObject({
        intent: 'check_bins',
        code: '# Selected notebook cell 1\npd.cut(ages, [0,18,65])',
        learner_answer: null,
      })
      await route.fulfill({
        json: {
          text: 'Code boundary check — your written answer has not been graded. Boundary 18 maps to bin 1.',
          model: 'none',
          route: 'deterministic',
          turn_id: 'fixture',
          source_note: 'Local boundary calculation only.',
        },
      })
    })
    await page.goto('/programs')
    await page.getByText('Full course notebook and files', { exact: true }).click()
    await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
    await page.getByText('Read or edit a notebook in this page', { exact: true }).click()
    await page.getByRole('button', { name: 'Open saved project notebook' }).click()
    await page.getByText('Local code checks', { exact: true }).click()
    expect(calls).toBe(0)
    const check = page.getByRole('button', { name: 'Check bin boundaries', exact: true })
    await check.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText(/your written answer has not been graded/)).toBeVisible()
    await expect(page.getByRole('button', { name: 'Listen to tutor response' })).toBeVisible()
    expect(calls).toBe(1)
  })
}
