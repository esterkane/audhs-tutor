import { expect, test } from '@playwright/test'

test('Home switches ready to unprepared and back before starting the selected topic', async ({ page }) => {
  let selected = 'python'
  let started = ''
  const skill = {
    id: 'python-lesson',
    title: 'Python variables',
    slug: 'python',
    domain: 'ai_ml',
    mastery: 0,
    unlocked: true,
    description: '',
    success_criteria: [],
    prerequisites: [],
    state: {},
  }
  await page.route('**/api/**', (route) => route.fulfill({ json: null }))
  await page.route('**/api/preferences', async (route) => {
    if (route.request().method() === 'PUT') selected = route.request().postDataJSON().value
    await route.fulfill({ json: { values: { 'goal.area': selected }, specs: [] } })
  })
  await page.route('**/api/areas', (route) =>
    route.fulfill({
      json: {
        areas: [
          { id: 'python', title: 'Python', active_lessons: 1 },
          {
            id: 'empty',
            title: 'Creative',
            active_lessons: 0,
          },
        ],
      },
    }),
  )
  await page.route('**/api/skills', (route) =>
    route.fulfill({ json: { skills: [skill], next_skill_id: selected === 'python' ? skill.id : null } }),
  )
  await page.route('**/api/sessions', async (route) => {
    expect(route.request().method()).toBe('POST')
    started = selected
    expect(selected).toBe('python')
    await route.fulfill({
      json: {
        id: 'fixture-session',
        next_skill: skill,
        state: { skill_id: skill.id },
        due_reviews: 0,
        plan: [],
      },
    })
  })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Start session', exact: true })).toBeEnabled()
  const area = page.getByRole('combobox', { name: 'Knowledge area' })
  await expect(area.getByRole('option', { name: 'Python · 1 activated lessons' })).toHaveCount(1)
  await area.selectOption('empty')
  const review = page.getByRole('link', { name: 'Review and activate a lesson', exact: true })
  await expect(review).toHaveAttribute('href', '/areas?area=empty')
  await expect(page.getByText(/Imported sources and drafts are preparation material/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Start session', exact: true })).toHaveCount(0)
  expect(started).toBe('')
  await area.selectOption('python')
  await expect(page.getByRole('button', { name: 'Start session', exact: true })).toBeEnabled()
  await expect(page.getByText('Python variables', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: 'Start session', exact: true }).click()
  await expect(page).toHaveURL(/\/session$/)
  expect(started).toBe('python')
})
