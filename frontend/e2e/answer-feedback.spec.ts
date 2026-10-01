import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
test(`checks the selected answer and offers question and feedback audio at ${width}px`, async ({ page }, testInfo) => {
  await page.setViewportSize({ width, height: 850 })
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
                title: 'Missingness',
                explanation: 'Cleaning changes representation.',
                example: 'Group A retains 90 rows; group B retains 60.',
                task: 'Compare',
                question: 'Why might equal rules have unequal effects?',
                hint: 'Compare retention.',
                criteria: 'Explain representation changes.',
                source: 'Fixture',
              },
            ],
          },
        ],
      },
    }),
  )
  let generations = 0
  await page.route('**/api/answers/recover-save', async (route) => {
    expect(route.request().postDataJSON()).toEqual({ receipt: 'synthetic-receipt' })
    await route.fulfill({ json: { answer_id: 'recovered-answer' } })
  })
  await page.route('**/api/playground/tutor', async (route) => {
    generations++
    const body = route.request().postDataJSON()
    expect(body.exercise).toContain('Group A retains 90')
    expect(body.learner_answer).toBe('Different proportions remain')
    expect(body.output).toBe('')
    expect(body.intent).toBe('check_answer')
    await route.fulfill({
      json: {
        text: 'Your answer identifies unequal retention. Explain how it changes representation.',
        model: 'fixture',
        route: 'fake',
        turn_id: 'fixture',
        save_error: 'Temporary save failure.',
        save_receipt: 'synthetic-receipt',
        source_note: 'Synthetic test feedback',
      },
    })
  })
  await page.goto('/programs')
  await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
  const check = page.getByRole('button', { name: 'Check my answer', exact: true })
  await expect(check).toBeDisabled()
  await page.getByLabel('Your explanation').fill('Different proportions remain')
  await expect(page.getByText(/OpenAI by default/)).toBeVisible()
  await check.focus()
  await page.keyboard.press('Enter')
  await expect(
    page.getByText('Your answer identifies unequal retention. Explain how it changes representation.'),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to question', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to feedback', exact: true })).toBeVisible()
  const retry = page.getByRole('button', { name: 'Retry saving', exact: true })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('link', { name: 'Open saved answer', exact: true })).toHaveAttribute('href', '/answers/recovered-answer')
  expect(generations).toBe(1)
  await page.screenshot({ path: testInfo.outputPath('answer-feedback.png'), fullPage: true })
  await page.getByLabel('Your explanation').fill('Changed reasoning')
  await expect(page.getByText(/Earlier feedback:/)).toBeVisible()
})

}
