import { expect, test, type Route } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`starter timeout keeps project notes and allows retry (${width}px)`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 850 })
    await page.clock.install()
    await page.route('**/local-learning/program.json', (route) => route.fulfill({ json: {
      title: 'Practice', courses: [{ id: 'fixture', title: 'Data practice', project: 'Count', status: 'Fixture',
        sections: [{ id: 'data', title: 'Inspect rows', explanation: 'Inspect first.', task: 'Count rows.',
          question: 'Why?', hint: 'Count.', criteria: 'Explain.', source: 'Fixture',
          practice: { notebook: '/local-learning/task.ipynb', dataset: '/local-learning/task.csv' } }],
      }],
    } }))
    await page.route('**/local-learning/task.ipynb', (route) => route.fulfill({ json: {
      nbformat: 4, metadata: { practice_checks: [{ name: 'Rows', criterion: 'Two rows', code: 'assert True' }] },
      cells: [{ cell_type: 'markdown', source: '## Count rows\nInspect before cleaning.' }, { cell_type: 'code', source: 'print(DATA_CSV)' }],
    } }))
    let ready = false
    let pending: Route | undefined
    await page.route('**/local-learning/task.csv', (route) => {
      if (!ready) { pending = route; return }
      return route.fulfill({ body: 'age\n18\n24\n' })
    })
    await page.goto('/programs')
    await page.getByRole('button', { name: 'Try', exact: true }).click()
    await page.getByRole('textbox', { name: 'Project notes', exact: true }).fill('Keep my observation.')
    await page.getByRole('button', { name: 'Open task starter notebook' }).click()
    await expect.poll(() => Boolean(pending)).toBe(true)
    await page.clock.fastForward(16000)
    await expect(page.getByRole('button', { name: 'Retry loading starter', exact: true })).toBeVisible()
    await expect(page.getByRole('region', { name: 'Notebook workspace', exact: true })).toHaveCount(0)
    ready = true
    const retry = page.getByRole('button', { name: 'Retry loading starter', exact: true })
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('region', { name: 'Notebook workspace', exact: true })).toBeVisible()
    await pending?.fulfill({ body: 'old,data' }).catch(() => {})
    await page.getByRole('combobox', { name: 'Notebook cell', exact: true }).selectOption('1')
    await page.getByRole('textbox', { name: 'Your prediction or explanation', exact: true }).fill('Keep my notebook prediction.')
    await page.reload()
    await expect(page.getByRole('region', { name: 'Notebook workspace', exact: true })).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Notebook cell', exact: true })).toHaveValue('1')
    await expect(page.getByRole('textbox', { name: 'Your prediction or explanation', exact: true })).toHaveValue('Keep my notebook prediction.')
    await expect(page.getByRole('button', { name: 'Return to task with results', exact: true })).toBeDisabled()
    await page.screenshot({ path: info.outputPath('restored-task-notebook.png'), fullPage: true })
    const back = page.getByRole('button', { name: 'Back to task without results', exact: true })
    await back.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue('Keep my observation.')
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  })
}
