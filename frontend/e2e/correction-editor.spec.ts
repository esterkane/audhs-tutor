import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`edit a correction and recover a committed save ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let reportId = ''
    try {
      const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(started)
      const session = await started.json()
      const next = await request.get(`${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`)
      await expectOk(next)
      const { item } = await next.json()
      const report = await request.post(`${API}/api/areas/feedback/questions`, { data: { assessment_id: item.id, verdict: 'bad', labels: ['too_vague'], note: 'Synthetic editor test' } })
      await expectOk(report); reportId = (await report.json()).id
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences#question-reports')
      await page.getByRole('button', { name: 'Show question reports' }).click()
      await page.getByRole('link', { name: 'Prepare a correction draft' }).click()
      await expect(page.getByText('This reveals the reference answers and grading criteria.', { exact: false })).toBeVisible()
      await page.getByRole('button', { name: 'Show reference answers and start a draft' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('heading', { name: 'Edit proposed question' })).toBeFocused()
      await page.getByLabel('Question wording').fill('Synthetic corrected wording?')
      const draftId = new URL(page.url()).searchParams.get('draft')!
      let writes = 0
      await page.route(`**/api/questions/correction-drafts/${draftId}`, async route => {
        if (route.request().method() !== 'PUT') return route.continue()
        writes++
        const response = await route.fetch()
        expect(response.status()).toBe(200)
        await route.abort('failed')
      })
      await page.getByRole('button', { name: 'Save correction draft' }).click()
      await expect(page.getByText(/The result is uncertain/)).toBeVisible()
      await page.getByLabel('Question wording').fill('Newer unsaved wording?')
      await page.reload()
      await expect(page.getByLabel('Question wording')).toHaveValue('Newer unsaved wording?')
      await page.getByRole('button', { name: 'Check save status' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Submitted version saved. Your newer edits are still unsaved.')).toBeVisible()
      expect(writes).toBe(1)
      await page.unroute(`**/api/questions/correction-drafts/${draftId}`)
      await page.getByRole('button', { name: 'Save correction draft' }).click()
      await expect(page.getByText('Draft version 3 saved. Practice is unchanged.')).toBeVisible()
      const saved = await request.get(`${API}/api/questions/correction-drafts/${draftId}`)
      await expectOk(saved)
      expect((await saved.json()).candidate.item.question).toBe('Newer unsaved wording?')
      await page.getByRole('heading', { name: 'Edit proposed question' }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: `/tmp/correction-editor-${width}.png`, fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await page.getByRole('link', { name: 'Back to reported questions' }).click()
      await page.goBack()
      await expect(page.getByLabel('Question wording')).toHaveValue('Newer unsaved wording?')
      expect((await (await request.get(`${API}/api/questions/${item.id}/practice`)).json()).status.state).toBe('active')
    } finally {
      if (reportId) await expectOk(await request.delete(`${API}/api/areas/feedback/questions/${reportId}`))
      await endOpenSession(request)
    }
  })
}
