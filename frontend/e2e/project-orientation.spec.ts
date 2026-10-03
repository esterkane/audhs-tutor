import { expect, test } from '@playwright/test'
import axe from 'axe-core'

const section = {
  id: 'first',
  title: 'Inspect the data',
  explanation: 'Count the missing values before changing rows.',
  task: 'Compare the groups.',
  question: 'Why compare groups?',
  hint: 'Think of representation.',
  criteria: 'Explain what changes.',
  source: 'Synthetic fixture',
}
const program = {
  title: 'Local study',
  courses: [
    { id: 'a', title: 'First course', project: 'Inspect', status: 'Fixture', sections: [section] },
    {
      id: 'b',
      title: 'Second course',
      project: 'Compare',
      status: 'Fixture',
      sections: [
        section,
        {
          ...section,
          id: 'second',
          title: 'Compare results',
          explanation: 'Compare the retained rows in each group.',
        },
      ],
    },
  ],
}
for (const width of [1280, 320]) {
  test(`project orientation and notebook return at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/local-learning/program.json', (route) => route.fulfill({ json: program }))
    await page.route('**/api/notebooks/status', (route) =>
      route.fulfill({ json: { status: 'idle', course_id: '', message: 'Ready to prepare' } }),
    )
    let starts = 0
    await page.route('**/api/notebooks/start', (route) => {
      starts++
      return route.abort()
    })
    await page.goto('/programs')
    await expect(page.getByRole('heading', { name: 'Inspect the data' })).toBeVisible()
    await expect(page.getByRole('combobox', { name: 'Course', exact: true })).toHaveCount(0)
    const change = page.getByText('Change course or project step', { exact: true })
    await change.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('combobox', { name: 'Course', exact: true }).selectOption('b')
    await page.getByRole('combobox', { name: 'Project step', exact: true }).selectOption('second')
    await expect(page.getByRole('heading', { name: 'Compare results' })).toBeFocused()
    await page.reload()
    await expect(page.getByRole('heading', { name: 'Compare results' })).toBeVisible()
    await page.getByRole('button', { name: 'Try', exact: true }).click()
    await page.getByRole('textbox', { name: 'Project notes', exact: true }).fill('Keep the original counts.')
    await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Full course notebook', exact: true })).toBeFocused()
    await expect(page.getByText(/This is the whole course notebook/)).toBeVisible()
    const back = page.getByRole('button', { name: 'Back to guided lesson' })
    await back.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue(
      'Keep the original counts.',
    )
    await expect(page.getByRole('heading', { name: 'Compare results' })).toBeFocused()
    expect(starts).toBe(0)
    await page.getByRole('button', { name: 'Understand', exact: true }).click()
    await page.evaluate(() => {
      document.documentElement.style.fontSize = '200%'
    })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.addScriptTag({ content: axe.source })
    const violations = await page.evaluate(
      async () =>
        (
          await (window as unknown as { axe: typeof axe }).axe.run('main', {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
          })
        ).violations,
    )
    expect(violations.map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) }))).toEqual([])
    await page.screenshot({ path: info.outputPath('project-orientation.png'), fullPage: true })
  })
}
