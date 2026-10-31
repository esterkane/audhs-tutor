import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const [language, width] of [['de', 390], ['en', 1280]] as const) {
  test(`literal Socratic question keeps ${language} and saved history at ${width}`, async ({ page, request }, testInfo) => {
    await endOpenSession(request)
    const preferences = await (await request.get(`${API}/api/preferences`)).json()
    const original = preferences.values['tutor.response_language']
    try {
      await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'tutor.response_language', value: language } }))
      const catalogue = await (await request.get(`${API}/api/skills`)).json()
      const skill = catalogue.skills.find((item: { id: string; unlocked: boolean }) => item.unlocked)
      expect(skill, 'an active unlocked concept in the current catalogue').toBeTruthy()
      const skillId = skill.id
      const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3, socratic: true, skill_id: skillId } })
      await expectOk(started)
      const session = await started.json()
      const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
      expect(index).toBeGreaterThanOrEqual(0)
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      const input = page.getByLabel('Ask about this lesson (optional)', { exact: true })
      await input.fill('Ask me one Socratic question about `a + [3]`, without giving the answer.')
      await page.screenshot({ path: testInfo.outputPath('saved-questioning-mode.png'), fullPage: true })
      const received = page.waitForResponse(response => response.url().includes('/api/tutor/stream') && response.request().method() === 'POST')
      await page.getByRole('button', { name: 'Send lesson question', exact: true }).click()
      const response = await received
      const blocks = (await response.text()).split('\n\n')
      const doneBlock = blocks.find(block => block.startsWith('event: done'))
      expect(doneBlock).toBeTruthy()
      const done = JSON.parse(doneBlock!.split('data: ')[1])
      expect(done.route).toBe('template')
      expect(done.model_call_id).toBeNull()
      expect(done.outcome).toBe('ok')
      expect(done.text).toBe(language === 'de'
        ? 'Auswerten von `a + [3]`: Welches Ergebnis erwartest du?'
        : 'For evaluating `a + [3]`, what result would you expect?')
      const tail = language === 'de' ? 'Welches Ergebnis erwartest du?' : 'what result would you expect?'
      await expect(page.getByText(tail, { exact: false })).toBeVisible()
      expect(done.answer_id).toBeTruthy()
      const saved = await request.get(`${API}/api/answers/${done.answer_id}`)
      await expectOk(saved)
      expect(JSON.stringify(await saved.json())).toContain(done.text)
      await page.reload()
      await page.getByRole('link', { name: 'Read saved explanations', exact: true }).click()
      await expect(page.getByText(tail, { exact: false })).toBeVisible()
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    } finally {
      await endOpenSession(request)
      await request.put(`${API}/api/preferences`, { data: { key: 'tutor.response_language', value: original } })
    }
  })
}
