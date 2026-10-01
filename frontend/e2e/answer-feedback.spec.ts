import { expect, test } from '@playwright/test'

test('checks the selected answer and offers question and feedback audio', async ({ page }) => {
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
  await page.route('**/api/playground/tutor', async (route) => {
    const body = route.request().postDataJSON()
    expect(body.exercise).toContain('Group A retains 90')
    expect(body.learner_answer).toBe('Different proportions remain')
    expect(body.output).toBe('')
    await route.fulfill({
      json: {
        text: 'Your answer identifies unequal retention. Explain how it changes representation.',
        model: 'fixture',
        route: 'fake',
        turn_id: 'fixture',
        source_note: 'Synthetic test feedback',
      },
    })
  })
  await page.goto('/programs')
  await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
  const check = page.getByRole('button', { name: 'Check my answer', exact: true })
  await expect(check).toBeDisabled()
  await page.getByLabel('Your explanation').fill('Different proportions remain')
  await check.click()
  await expect(
    page.getByText('Your answer identifies unequal retention. Explain how it changes representation.'),
  ).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to question', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Listen to feedback', exact: true })).toBeVisible()
  await page.getByLabel('Your explanation').fill('Changed reasoning')
  await expect(page.getByText(/Earlier feedback:/)).toBeVisible()
})
