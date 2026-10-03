import { expect, test } from '@playwright/test'

for (const width of [390, 800, 1280]) {
  test(`Home puts the saved topic first at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) =>
      route.fulfill({
        json: {
          id: 'fixture',
          active_skill: { id: 'topic', title: 'Comparing groups' },
          state: { skill_id: 'topic', block_status: 'running', phase: 'review', plan_complete: false },
        },
      }),
    )
    await page.goto('/')
    const resume = page.getByRole('button', { name: /^Resume previous session: Comparing groups/ })
    await expect(resume).toBeVisible()
    await expect(page.getByText('Next: continue your saved review.')).toBeVisible()
    const options = page.getByText('Session options', { exact: true })
    await expect(options.locator('..')).not.toHaveAttribute('open')
    const box = await resume.boundingBox()
    expect(box!.y).toBeLessThan((await options.boundingBox())!.y)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await resume.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/review$/)
  })
}

test('an empty chosen topic offers activation instead of a dead Start button', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.route('**/api/sessions/current', (route) => route.fulfill({ json: null }))
  await page.route('**/api/preferences', (route) =>
    route.fulfill({ json: { values: { 'goal.area': 'empty-topic' } } }),
  )
  await page.route('**/api/skills', (route) => route.fulfill({ json: { skills: [], next_skill_id: null } }))
  await page.route('**/api/areas', (route) =>
    route.fulfill({
      json: {
        areas: [
          {
            id: 'empty-topic',
            title: 'Local inference',
            terms: ['local'],
            description: '',
            documents: 1,
            courses: [],
            draft_ids: [],
            related: [],
          },
        ],
        total_documents: 1,
        unassigned_documents: 0,
      },
    }),
  )
  await page.goto('/')
  const startCard = page.getByLabel('Start or resume learning')
  await expect(startCard.getByText('New session topic: Local inference')).toBeVisible()
  await expect(startCard.getByRole('button', { name: 'Start session', exact: true })).toHaveCount(0)
  const activate = startCard.getByRole('link', { name: 'Review and activate a lesson', exact: true })
  await expect(activate).toHaveAttribute('href', '/areas?area=empty-topic')
  await activate.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/\/areas\?area=empty-topic$/)
})
