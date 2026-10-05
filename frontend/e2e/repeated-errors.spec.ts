import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

test('two incorrect answers retain feedback, help and explicit pause', async ({ page, request }, info) => {
  const narrow = true
    await endOpenSession(request)
    try {
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
      await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
      await expectOk(
        await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
      )
      await expectOk(
        await request.post(`${API}/api/sessions/${session.id}/checkpoint`, {
          data: { phase: 'assess', skill_id: freshDeterministicSkill() },
        }),
      )
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()

      let submitted = 0
      page.on('request', req => {
        if (req.method() === 'POST' && req.url().endsWith('/api/assess/attempt')) submitted++
      })
      const attempts: string[] = []
      for (let turn = 0; turn < 2; turn++) {
        const choices = page.getByRole('group', { name: 'Your answer', exact: true })
        if (await choices.count()) await choices.getByRole('button').last().click()
        else await page.getByRole('textbox', { name: 'Your answer', exact: true }).fill('0')
        const reply = page.waitForResponse(r => r.url().endsWith('/api/assess/attempt') && r.request().method() === 'POST')
        await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
        const grade = await (await reply).json()
        expect(grade.correct).toBe(false)
        attempts.push(grade.attempt_id)
        await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toBeVisible()
        await expect(page.getByRole('button', { name: "I don't understand yet — explain the idea", exact: true })).toBeVisible()
        await expect(page.getByRole('button', { name: 'Revisit the explanation', exact: true })).toBeEnabled()
        await expect(page.getByRole('button', { name: 'Continue the plan', exact: true })).toBeEnabled()
        expect(submitted).toBe(turn + 1)
        if (turn === 0) {
          const next = page.getByRole('button', { name: 'Try another question (optional)', exact: true })
          await next.focus()
          await page.keyboard.press('Enter')
          await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeVisible()
          await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toHaveCount(0)
        }
      }
      expect(new Set(attempts).size).toBe(2)
      await page.reload()
      await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toBeVisible()
      expect(submitted).toBe(2)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: info.outputPath('repeated-errors.png'), fullPage: true })
      const pause = page.getByRole('button', { name: 'Pause and return Home', exact: true })
      await pause.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByRole('button', { name: /^Continue$/ })).toBeVisible()
      expect(submitted).toBe(2)
    } finally {
      await endOpenSession(request)
    }
})
