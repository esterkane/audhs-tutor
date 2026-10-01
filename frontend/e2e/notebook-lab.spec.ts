import { expect, test } from '@playwright/test'

test('prepares a notebook from the app without a terminal or automatic cell execution', async ({ page }) => {
  await page.route('**/local-learning/program.json', (route) =>
    route.fulfill({
      json: {
        title: 'Local practice',
        courses: [{ id: 'fixture', title: 'Example', project: 'Study', status: 'Fixture', sections: [] }],
      },
    }),
  )
  await page.route('**/api/notebooks/status', (route) =>
    route.fulfill({ json: { status: 'idle', message: 'Ready to prepare', url: null, course_id: '' } }),
  )
  let requests = 0
  await page.route('**/api/notebooks/start', (route) => {
    requests++
    expect(route.request().postDataJSON()).toEqual({ course_id: 'fixture', install: false })
    return route.fulfill({
      json: {
        status: 'ready',
        message: 'Prepared',
        url: 'http://127.0.0.1:8890/lab/tree/fixture/task.ipynb?token=fixture',
        course_id: 'fixture',
      },
    })
  })
  await page.goto('/programs')
  await page.getByRole('button', { name: 'Notebook workspace', exact: true }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  const prepare = page.getByRole('button', { name: 'Prepare and start notebook lab' })
  await prepare.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('link', { name: 'Open prepared notebook in Jupyter' })).toHaveAttribute(
    'href',
    /\/fixture\/task.ipynb/,
  )
  expect(requests).toBe(1)
})
