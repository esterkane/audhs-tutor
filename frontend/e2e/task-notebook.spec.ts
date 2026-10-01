import { expect, test } from '@playwright/test'

test('task starter runs locally and returns checked output to preserved notes', async ({ page }) => {
  await page.route('**/local-learning/program.json', (route) =>
    route.fulfill({
      json: {
        title: 'Practice',
        courses: [
          {
            id: 'fixture',
            title: 'Data practice',
            project: 'Inspect data',
            status: 'Synthetic',
            sections: [
              {
                id: 'data',
                title: 'Inspect rows',
                explanation: 'Count before cleaning.',
                task: 'Print the row count.',
                question: 'Why?',
                hint: 'Compare.',
                criteria: 'Explain.',
                source: 'Fixture',
                practice: { notebook: '/local-learning/task.ipynb', dataset: '/local-learning/task.csv' },
              },
            ],
          },
        ],
      },
    }),
  )
  await page.route('**/local-learning/task.ipynb', (route) =>
    route.fulfill({
      json: {
        nbformat: 4,
        metadata: { practice_checks: [{ name: 'Rows', criterion: 'Two rows', code: 'assert len(rows)==2' }] },
        cells: [
          { cell_type: 'markdown', source: '## Starter\nCount the fixture rows.' },
          {
            cell_type: 'code',
            source:
              'import csv, io\nrows=list(csv.DictReader(io.StringIO(DATA_CSV)))\nassert len(rows)==2\nprint("PASS: two rows")',
          },
        ],
      },
    }),
  )
  await page.route('**/local-learning/task.csv', (route) => route.fulfill({ body: 'age\n18\n24\n' }))
  await page.goto('/programs')
  await page.getByRole('button', { name: 'Try', exact: true }).click()
  await page.getByLabel('Project notes').fill('My initial observation')
  await page.getByRole('button', { name: 'Open task starter notebook' }).click()
  await expect(page.getByRole('heading', { name: 'Notebook: Inspect rows' })).toBeFocused()
  await page.getByRole('button', { name: 'Run all and check' }).click()
  const done = page.getByRole('button', { name: 'Return to task with results' })
  await expect(done).toBeEnabled({ timeout: 45000 })
  await page.setViewportSize({ width: 390, height: 844 })
  await done.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByLabel('Project notes')).toContainText('PASS: two rows')
  await expect(page.getByLabel('Project notes')).toContainText('My initial observation')
  await expect(page.getByRole('heading', { name: 'Your next project task' })).toBeFocused()
  await page.reload()
  await expect(page.getByLabel('Project notes')).toContainText('PASS: two rows')
})
