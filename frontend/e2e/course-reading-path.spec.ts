import { expect, test } from '@playwright/test'
import axe from 'axe-core'

const section = {
  id: 'read', title: 'Training-only fitting', explanation: 'prose '.repeat(401),
  task: 'Record which values fit the parameter.', question: 'Which split supplies the fitted value?',
  hint: 'Consider the training split.', criteria: 'Distinguish fit from transform.', source: 'Synthetic course fixture',
}
const courses = [
  { id: 'a', title: 'Course A — Python', project: 'Read', status: 'Fixture', sections: [section] },
  { id: 'b', title: 'Kurs B — Daten', project: 'Read', status: 'Fixture', sections: [{ ...section, explanation: 'Eine kurze Erklärung.' }] },
]
for (const width of [390, 1280]) test(`course path and reading estimates preserve work at ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: { title: 'Synthetic programme', courses } }))
  let modelCalls = 0
  page.on('request', request => { if (/tutor\/(stream|study)/.test(request.url()) && request.method() === 'POST') modelCalls++ })
  await page.goto('/programs?course=a&step=read')
  const path = page.getByRole('navigation', { name: 'Learning path' })
  await expect(path).toHaveText(/Course A — Python.*Training-only fitting.*Understand/)
  await expect(page.getByText('Reading time: about 3 min (estimate)', { exact: true })).toBeVisible()
  const estimate = page.getByText('Reading time: about 3 min (estimate)', { exact: true })
  await estimate.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(/not your measured pace or time remaining/)).toBeVisible()
  await page.getByRole('button', { name: 'Try', exact: true }).click()
  await page.getByRole('textbox', { name: 'Project notes', exact: true }).fill('Keep these training-only findings.')
  await expect(path).toHaveText(/Course A — Python.*Try/)
  await expect(page.getByText('Reading time: about 1 min (estimate)', { exact: true })).toBeVisible()
  await page.goto('/programs?course=b&step=read')
  await expect(path).toHaveText(/Kurs B — Daten.*Understand/)
  await expect(page.getByText('Reading time: about 1 min (estimate)', { exact: true })).toBeVisible()
  await page.goto('/programs?course=a&step=read')
  await expect(path).toHaveText(/Course A — Python.*Try/)
  await expect(page.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue('Keep these training-only findings.')
  await expect(page.getByText(/Continue at Try/)).toBeVisible()
  await page.reload()
  await expect(path).toHaveText(/Course A — Python.*Try/)
  await expect(page.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue('Keep these training-only findings.')
  await page.getByRole('button', { name: 'Focus mode', exact: true }).click()
  await expect(path).toBeVisible()
  await page.keyboard.press('Escape')
  await page.addScriptTag({ content: axe.source })
  expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  expect(modelCalls).toBe(0)
  await page.screenshot({ path: info.outputPath('reading-path.png'), fullPage: true })
})
