import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`notebook focus and Socratic follow-up at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'fixture-session' } }))
    await page.route('**/local-learning/program.json', (route) =>
      route.fulfill({
        json: {
          title: 'Practice',
          courses: [
            {
              id: 'fixture',
              title: 'Example',
              project: 'Study',
              status: 'Fixture',
              sections: [],
              notebook: '/local-learning/example.ipynb',
            },
          ],
        },
      }),
    )
    await page.route('**/local-learning/example.ipynb', (route) =>
      route.fulfill({
        json: {
          nbformat: 4,
          nbformat_minor: 5,
          metadata: {},
          cells: [
            { cell_type: 'markdown', source: '# Inspect\nLook at missing data.', metadata: {} },
            { cell_type: 'code', source: 'count = 2', metadata: {}, outputs: [], execution_count: null },
            { cell_type: 'markdown', source: '# Compare\nCompare group retention.', metadata: {} },
            {
              cell_type: 'code',
              source: 'retained = [90, 60]',
              metadata: {},
              outputs: [],
              execution_count: null,
            },
          ],
        },
      }),
    )
    let requests = 0
    await page.route('**/api/playground/tutor', async (route) => {
      const body = route.request().postDataJSON()
      expect(body.exercise).toContain('Compare group retention')
      if (requests === 1) {
        expect(body.question).toContain('My answer to your last question')
        expect(body.history).toHaveLength(2)
      }
      const text =
        requests++ === 0
          ? 'Why compare proportions rather than counts?'
          : 'You identified unequal group sizes. What would you compare next?'
      await route.fulfill({
        json: { text, model: 'fixture', route: 'fake', turn_id: 'fixture', source_note: 'Synthetic' },
      })
    })
    await page.goto('/programs')
    await page.getByRole('button', { name: 'Notebook workspace', exact: true }).click()
    await page.getByRole('button', { name: 'Open saved project notebook' }).click()
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('2')
    await expect(page.getByRole('combobox', { name: 'Notebook cell', exact: true })).toHaveValue('0')
    await expect(page.getByText('Discussing: Step — Compare')).toBeVisible()
    const socratic = page.getByRole('button', { name: 'Ask me a Socratic question', exact: true })
    await socratic.focus()
    await page.keyboard.press('Enter')
    const answer = page.getByLabel('Your answer to the tutor’s question', { exact: true })
    await expect(answer).toBeFocused()
    await answer.fill('The groups have different sizes.')
    await page.getByRole('button', { name: 'Discuss my answer', exact: true }).click()
    await expect(
      page.getByText('You identified unequal group sizes. What would you compare next?'),
    ).toBeVisible()
    await page.getByText('Earlier messages (2)', { exact: true }).click()
    await expect(page.getByText('Why compare proportions rather than counts?', { exact: true })).toBeVisible()
    await answer.fill('Keep this draft')
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('0')
    await expect(page.getByText('Discussing: Step — Inspect')).toBeVisible()
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('2')
    await expect(answer).toHaveValue('Keep this draft')
    expect(requests).toBe(2)
    await page.getByRole('button', { name: 'Explain instead', exact: true }).click()
    const draft = page.getByLabel('Your tutor message or response', { exact: true })
    await expect(draft).toHaveValue('Keep this draft')
    for (const label of ['Shorter', 'Smaller steps', 'Show an example']) {
      const control = page.getByRole('button', { name: label, exact: true })
      await control.focus()
      await page.keyboard.press('Enter')
      await expect(control).toBeEnabled()
      await expect(draft).toHaveValue('Keep this draft')
      await expect(page.getByText('Discussing: Step — Compare')).toBeVisible()
    }
    expect(requests).toBe(6)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
