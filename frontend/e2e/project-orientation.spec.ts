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
    const assertReflow = async () => {
      const overflow = await page.evaluate(() => ({
        width: innerWidth,
        scrollWidth: document.documentElement.scrollWidth,
        elements: [...document.querySelectorAll('body *')].flatMap((node) => {
          const rect = node.getBoundingClientRect()
          return rect.width && (rect.right > innerWidth + 1 || rect.left < -1)
            ? [
                {
                  tag: node.tagName,
                  text: node.textContent?.slice(0, 100),
                  class: node.className,
                  left: rect.left,
                  right: rect.right,
                  width: rect.width,
                },
              ]
            : []
        }),
      }))
      expect(overflow.scrollWidth, JSON.stringify(overflow, null, 2)).toBeLessThanOrEqual(width + 1)
    }
    // Keep the original 200% text check, then exercise wider text metrics independently of
    // the platform's system font. Neither check clips overflow or reduces text size.
    await assertReflow()
    await page.evaluate(() => {
      document.body.style.letterSpacing = '0.12em'
    })
    await assertReflow()
    for (const control of await page
      .getByRole('navigation', { name: 'Learning steps' })
      .getByRole('button')
      .all()) {
      expect(await control.evaluate((node) => node.scrollHeight <= node.clientHeight + 1)).toBe(true)
      expect(await control.evaluate((node) => node.scrollWidth <= node.clientWidth + 1)).toBe(true)
    }
    await page.getByText('Bookmark and saved work', { exact: true }).click()
    await expect(page.getByRole('combobox', { name: 'My bookmark' })).toBeVisible()
    await assertReflow()
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


test('project links and browser history preserve the selected step', async ({ page }) => {
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: program }))
  await page.goto('/programs?course=b&step=second')
  await expect(page.getByRole('heading', { name: 'Compare results', exact: true })).toBeVisible()
  await page.getByText('Change course or project step', { exact: true }).click()
  await page.getByRole('combobox', { name: 'Project step', exact: true }).selectOption('first')
  await expect(page).toHaveURL(/step=first/)
  await page.goBack()
  await expect(page.getByRole('heading', { name: 'Compare results', exact: true })).toBeVisible()
  await expect.poll(() => page.evaluate(() => JSON.parse(localStorage.getItem('project-study-location:v1') ?? 'null')?.sectionId)).toBe('second')
  await page.goForward()
  await expect(page.getByRole('heading', { name: 'Inspect the data', exact: true })).toBeVisible()
})


test('missing project link discloses fallback without a saved-place claim', async ({ page }) => {
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: program }))
  await page.goto('/programs?course=missing&step=missing')
  await expect(page.getByText(/linked course or step could not be found/)).toBeVisible()
  await expect(page.getByText('Your place is saved in this browser.', { exact: true })).toHaveCount(0)
})
