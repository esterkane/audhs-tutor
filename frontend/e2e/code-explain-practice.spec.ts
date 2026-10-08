import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, reachLearnBlock, skillIdBySlug } from './helpers'

for (const width of [390, 1280]) {
  test(`explain-back controls preserve the code workspace ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let questionId = ''
    try {
      await reachLearnBlock(page)
      const session = await currentSession(request)
      const skillId = await skillIdBySlug(request, 'attn-scaled')
      await expectOk(await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, { data: { skill_id: skillId } }))
      const response = await request.get(`${API}/api/exercises/for-skill/${skillId}`)
      await expectOk(response)
      questionId = (await response.json()).check_assessment_id
      await page.setViewportSize({ width, height: 900 })
      await page.reload()
      await page.getByText(/^Code exercise \(optional/).click()
      await page.getByRole('button', { name: 'Switch to the plain editor' }).click()
      const editor = page.getByRole('textbox', { name: /Your code/ })
      await editor.fill('print("keep my code")')
      for (let level = 1; level <= 3; level++) {
        await page.getByRole('button', { name: `Hint ${level} of 3` }).click()
        await expect(page.getByRole('button', { name: level < 3 ? `Hint ${level + 1} of 3` : 'Show the full solution' })).toBeVisible()
      }
      await page.getByRole('button', { name: 'Show the full solution' }).click()
      await page.getByRole('button', { name: 'Yes, show it' }).click()
      const answer = page.locator('#check-answer')
      await answer.fill('My explanation is still a draft.')
      const panel = page.getByLabel('Explain-back practice choices')
      await panel.getByRole('button', { name: 'Question practice options' }).focus()
      await page.keyboard.press('Enter')
      await panel.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Check my answer' })).toBeDisabled()
      await expect(editor).toHaveValue('print("keep my code")')
      await expect(answer).toHaveValue('My explanation is still a draft.')
      await panel.screenshot({ path: `/tmp/code-explain-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await panel.getByRole('button', { name: 'Restore this question', exact: true }).click()
      await panel.getByRole('button', { name: 'Refresh restored explain-back question' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: 'Check my answer' })).toBeEnabled()
      await expect(panel).toBeFocused()
      await expect(answer).toHaveValue('My explanation is still a draft.')
      await expect(editor).toHaveValue('print("keep my code")')
    } finally {
      if (questionId) {
        const view = await (await request.get(`${API}/api/questions/${questionId}/practice`)).json()
        if (view.status.state === 'suspended') await expectOk(await request.post(`${API}/api/questions/${questionId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } }))
      }
      await endOpenSession(request)
    }
  })
}
