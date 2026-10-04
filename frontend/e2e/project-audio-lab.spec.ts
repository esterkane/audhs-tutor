import { expect, test } from '@playwright/test'

const section = { id: 'frequency', title: 'Compare frequencies', explanation: 'Frequency counts cycles per second.', task: 'Compare two frequencies.', question: 'What changes?', hint: 'Cycles.', criteria: 'Describe frequency.', source: 'Synthetic fixture', audioLab: { lesson: 'frequency', purpose: 'Compare cycle spacing while keeping amplitude constant.' } }
const program = { title: 'Signal practice', courses: [{ id: 'signals', title: 'Signals', project: 'Compare tones', status: 'Fixture', sections: [section] }] }
for (const width of [390, 1280]) {
  test(`authored audio experiment preserves project context ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/local-learning/program.json', route => route.fulfill({ json: program }))
    const writes: string[] = []
    page.on('request', request => { if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url()) })
    await page.addInitScript(() => {
      const original = window.AudioContext
      Object.assign(window, { audioStarts: 0 })
      window.AudioContext = new Proxy(original, { construct(target, args) {
        const tracker = window as unknown as { audioStarts: number }
        tracker.audioStarts++
        return Reflect.construct(target, args)
      } })
    })
    await page.goto('/programs?course=signals&step=frequency')
    await page.getByRole('button', { name: 'Try', exact: true }).click()
    await page.getByRole('textbox', { name: 'Project notes', exact: true }).fill('Keep amplitude constant.')
    await page.getByText('Related audio experiment', { exact: true }).click()
    const link = page.getByRole('link', { name: 'Open linked audio lesson', exact: true })
    await link.focus(); await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Open linked lesson: Frequency', exact: true })).toBeVisible()
    await page.reload()
    await page.getByRole('button', { name: 'Open linked lesson: Frequency', exact: true }).click()
    await expect(page.getByRole('combobox', { name: 'Learning step', exact: true })).toHaveValue('1')
    expect(await page.evaluate(() => (window as unknown as { audioStarts: number }).audioStarts)).toBe(0)
    expect(writes).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: info.outputPath('project-audio.png'), fullPage: true })
    await page.getByRole('link', { name: 'Return to project step: Compare frequencies', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('textbox', { name: 'Project notes', exact: true })).toHaveValue('Keep amplitude constant.')
  })
}

test('missing audio relation offers recovery without changing the lab', async ({ page }) => {
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: program }))
  await page.goto('/playground/visualizer?project_course=signals&project_step=missing')
  await expect(page.getByText('This project step has no available audio-lab link.')).toBeVisible()
  await expect(page.getByRole('button', { name: /Open linked lesson:/ })).toHaveCount(0)
  await expect(page.getByRole('link', { name: 'Return to projects', exact: true })).toHaveAttribute('href', '/programs')
})


test('changed authored lesson does not silently substitute a new experiment', async ({ page }) => {
  await page.route('**/local-learning/program.json', route => route.fulfill({ json: program }))
  await page.goto('/playground/visualizer?project_course=signals&project_step=frequency&project_lesson=amplitude')
  await expect(page.getByText(/linked audio lesson changed/)).toBeVisible()
  await expect(page.getByRole('button', { name: /Open linked lesson:/ })).toHaveCount(0)
})
