import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

const starterCode = `# Illustrative data, not your dataset.
sample_data = {'values': [1, 2]}

def practice(data):
    # Implement the task described above.
    raise NotImplementedError("Write your implementation here.")

# After completing practice, uncomment this to try your result:
# print(practice(sample_data))`
const starterReply = 'Start with one small example.\n\nYour task: Replace the placeholder inside `practice(data)` and return the sum of the values in data["values"].\n\n```python\n' + starterCode + '\n```\n\nThis template has not been run.'

for (const width of [390, 1280]) {
  test(`lesson experiment returns with saved work ${width}`, async ({ page, request }, info) => {
    await endOpenSession(request)
    try {
      await page.setViewportSize({ width, height: 900 })
      await page.addInitScript(() => localStorage.setItem('code-editor:plain', '1'))
      const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(started)
      const session = await started.json()
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.goto('/')
      await page.getByRole('button', { name: /^Resume previous session/ }).click()
      const input = page.getByLabel('Ask about this lesson (optional)')
      await input.fill('Keep my lesson question')
      await page.getByRole('main').getByText('Work alongside', { exact: true }).focus()
      await page.keyboard.press('Space')
      await expect(page.getByRole('heading', { name: 'Working alongside', exact: true })).toBeVisible()
      await page.getByText('Try a coding experiment', { exact: true }).click()
      await page.getByRole('link', { name: 'Open lesson experiment' }).click()
      await expect(page.getByRole('heading', { name: 'Lesson experiment', exact: true })).toBeVisible()
      const location = page.url()
      const code = page.getByRole('textbox', { name: /Python code/ })
      await code.fill('print("lesson-specific work")')
      await page.getByRole('link', { name: /^Return to lesson:/ }).focus()
      await page.keyboard.press('Enter')
      await expect(input).toHaveValue('Keep my lesson question')
      await expect(page.getByRole('heading', { name: 'Working alongside', exact: true })).toBeVisible()
      await page.reload()
      await expect(page.getByRole('heading', { name: 'Working alongside', exact: true })).toBeVisible()
      await expect(input).toHaveValue('Keep my lesson question')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('alongside-return.png'), fullPage: true })
      await page.goto(location)
      await expect(code).toHaveValue('print("lesson-specific work")')
      await page.reload()
      await expect(code).toHaveValue('print("lesson-specific work")')
      const tutorBodies: Record<string, unknown>[] = []
      await page.route('**/api/playground/tutor', async route => {
        tutorBodies.push(route.request().postDataJSON())
        await route.fulfill({ json: { text: starterReply, model: 'fixture', route: 'local', source_note: 'Reference passages supplied.', sources: [{ chunk_id: 'fixture-source', citation: 'Synthetic reference', text: 'Vectors have components.' }], turn_id: 'fixture' } })
      })
      await page.getByRole('textbox', { name: 'Ask about your code' }).fill('Explain my experiment')
      await page.getByRole('button', { name: 'Suggest starter code', exact: true }).click()
      await expect(page.getByRole('textbox', { name: 'Ask about your code' })).toHaveValue('Explain my experiment')
      await expect(page.getByText('Start with one small example.', { exact: true })).toBeVisible()
      expect(tutorBodies).toHaveLength(1)
      expect(tutorBodies[0].intent).toBe('starter')
      expect(tutorBodies[0].question).toContain('Suggest one small starter Python example')
      expect(tutorBodies[0].session_id).toBe(session.id)
      expect(tutorBodies[0].lesson_origin).toEqual({ skill_id: new URL(location).searchParams.get('lesson_skill') })
      expect(tutorBodies[0].exercise).toContain('Lesson:')
      expect(tutorBodies[0].learning_context).toMatchObject({ target_id: expect.stringContaining(`lesson:${session.id}:`) })
      const sources = page.getByText('Reference passages supplied to the tutor (1)', { exact: true })
      await sources.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Vectors have components.', { exact: true })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect(await page.getByLabel('Tutor conversation').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.reload()
      await sources.click()
      await expect(page.getByText('Vectors have components.', { exact: true })).toBeVisible()
      const addExample = page.getByRole('button', { name: 'Add Python example 1 below my code', exact: true })
      await addExample.focus()
      await page.keyboard.press('Enter')
      await expect(code).toHaveValue('print("lesson-specific work")\n\n' + starterCode)
      await expect(page.getByText('Run your code to see what it produces.', { exact: true })).toBeVisible()
      await expect(addExample).toBeDisabled()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      expect(await page.getByLabel('Tutor conversation').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('linked-experiment.png'), fullPage: true })
      await page.getByRole('button', { name: 'Undo adding example', exact: true }).click()
      await expect(code).toHaveValue('print("lesson-specific work")')
      await page.goto('/playground')
      await expect(code).not.toHaveValue('print("lesson-specific work")')
      await endOpenSession(request)
      await page.goto(location)
      await expect(page.getByText(/This lesson is no longer the current learning context/)).toBeVisible()
      await expect(page.getByRole('button', { name: 'Run code', exact: true })).toHaveCount(0)
    } finally { await endOpenSession(request) }
  })
}
