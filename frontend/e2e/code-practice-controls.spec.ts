import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, reachLearnBlock, skillIdBySlug } from './helpers'

for (const width of [390, 1280]) {
  test(`code exclusion keeps the editor and restores explicitly ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let assessmentId = ''
    try {
      await reachLearnBlock(page)
      const session = await currentSession(request)
      const skillId = await skillIdBySlug(request, 'attn-scaled')
      await expectOk(await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, { data: { skill_id: skillId } }))
      const exercise = await request.get(`${API}/api/exercises/for-skill/${skillId}`)
      await expectOk(exercise)
      assessmentId = (await exercise.json()).assessment_id
      await page.setViewportSize({ width, height: 900 })
      await page.reload()
      await page.getByText(/^Code exercise \(optional/).click()
      await page.getByRole('button', { name: 'Switch to the plain editor' }).click()
      const editor = page.getByRole('textbox', { name: /Your code/ })
      await editor.fill('print("keep this draft")')
      const options = page.getByRole('button', { name: 'Question practice options' })
      await options.focus()
      await page.keyboard.press('Enter')
      await page.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      await expect(page.getByText('This exercise is excluded. You can keep editing and running your code. Restore it before submitting another code attempt.')).toBeVisible()
      await expect(editor).toHaveValue('print("keep this draft")')
      await expect(page.getByRole('button', { name: 'Run', exact: true })).toBeEnabled()
      await expect(page.getByRole('button', { name: 'Hint 1 of 3' })).toBeDisabled()
      await page.getByLabel('Code practice choices').screenshot({ path: `/tmp/code-practice-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await page.getByRole('button', { name: 'Restore this question', exact: true }).click()
      await page.getByRole('button', { name: 'Refresh restored exercise' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Refresh restored exercise' })).toHaveCount(0)
      await expect(page.getByLabel('Code practice choices')).toBeFocused()
      await expect(editor).toHaveValue('print("keep this draft")')
      await expect(page.getByRole('button', { name: 'Hint 1 of 3' })).toBeEnabled()
    } finally {
      if (assessmentId) {
        const view = await (await request.get(`${API}/api/questions/${assessmentId}/practice`)).json()
        if (view.status.state === 'suspended') await expectOk(await request.post(`${API}/api/questions/${assessmentId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } }))
      }
      await endOpenSession(request)
    }
  })
}
