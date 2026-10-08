import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`listening question choice keeps clip position ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let assessmentId = ''
    try {
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const next = await request.get(`${API}/api/assess/next?session_id=${session.id}&skill_id=${freshDeterministicSkill()}`)
      await expectOk(next)
      const { item } = await next.json()
      assessmentId = item.id
      await page.route('**/api/listening/lessons/clip', route => route.fulfill({ json: {
        document_id: 'clip', title: 'Synthetic clip', media_url: '/fixture-audio', language: 'en', next_index: 0,
        sections: [{ chunk_id: 'chunk', t_start: 0, t_end: 20, text: 'Synthetic transcript', index: 0 }],
      } }))
      await page.route('**/api/listening/lessons/clip/sections/0/task', route => route.fulfill({ json: {
        item, origin: 'model', validated: true, problems: [], citation: null,
        clip: { t_start: 0, t_end: 20, chunk_id: 'chunk' },
      } }))
      await page.addInitScript(() => {
        HTMLMediaElement.prototype.play = function () { return Promise.resolve() }
        HTMLMediaElement.prototype.pause = function () { this.dispatchEvent(new Event('pause')) }
      })
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.evaluate(id => {
        const el = document.createElement('div')
        el.id = 'fixture'
        el.dataset.sessionId = id
        el.className = 'm-4'
        document.body.append(el)
      }, session.id)
      await page.addScriptTag({ type: 'module', url: '/src/test/browser/listening-coordination.tsx' })
      const fixture = page.locator('#fixture')
      await fixture.getByRole('button', { name: 'Go to the question', exact: true }).click()
      await fixture.getByRole('button', { name: item.options[0], exact: true }).click()
      await fixture.locator('audio').evaluate((el: HTMLAudioElement) => { el.currentTime = 5 })
      await fixture.getByRole('button', { name: 'Question practice options' }).focus()
      await page.keyboard.press('Enter')
      await fixture.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      await expect(fixture.getByRole('button', { name: 'Check', exact: true })).toBeDisabled()
      expect(await fixture.locator('audio').evaluate((el: HTMLAudioElement) => el.currentTime)).toBe(5)
      await fixture.getByLabel('Listening practice choices').screenshot({ path: `/tmp/listening-practice-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await fixture.getByRole('button', { name: 'Restore this question', exact: true }).click()
      await fixture.getByRole('button', { name: 'Refresh restored question' }).focus()
      await page.keyboard.press('Enter')
      await expect(fixture.getByLabel('Listening practice choices')).toBeFocused()
      await expect(fixture.getByRole('button', { name: 'Check', exact: true })).toBeEnabled()
      expect(await fixture.locator('audio').evaluate((el: HTMLAudioElement) => el.currentTime)).toBe(5)
    } finally {
      if (assessmentId) {
        const view = await (await request.get(`${API}/api/questions/${assessmentId}/practice`)).json()
        if (view.status.state === 'suspended') await expectOk(await request.post(`${API}/api/questions/${assessmentId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } }))
      }
      await endOpenSession(request)
    }
  })
}
