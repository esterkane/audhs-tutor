import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, finishReview } from './helpers'

for (const width of [1280, 390]) {
  for (const phase of ['teach', 'assess', 'review'] as const) {
    test(`pause preserves ${phase} checkpoint at ${width}px`, async ({ page, request }, info) => {
      await endOpenSession(request)
      try {
        await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
        await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
        const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
        await expectOk(started)
        const session = await started.json()
        const index = session.plan.findIndex((block: { type: string }) =>
          phase === 'review' ? block.type === 'retrieval' : block.type === 'new_material',
        )
        expect(index).toBeGreaterThanOrEqual(0)
        await expectOk(await request.post(`${API}/api/plan/blocks/start`, {
          data: { session_id: session.id, index },
        }))
        if (phase === 'assess') {
          await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, {
            data: { phase: 'assess' },
          }))
        }
        await page.setViewportSize({ width, height: 900 })
        await page.goto('/')
        await page.getByRole('button', { name: /^Continue$/ }).click()
        const pause = page.getByRole('button', { name: 'Pause and return Home', exact: true })
        await expect(pause).toBeVisible()
        if (phase === 'teach') await page.getByLabel('Ask about this lesson (optional)').fill('Keep this unfinished question.')
        const before = await currentSession(request)
        const writes: string[] = []
        page.on('request', (req) => {
          if (req.method() !== 'GET' && req.url().includes('/api/')) writes.push(req.url())
        })
        await pause.focus()
        await page.keyboard.press('Enter')
        await expect(page).toHaveURL(/\/$/)
        await expect(page.getByRole('button', { name: /^Continue$/ })).toBeVisible()
        expect(await currentSession(request)).toEqual(before)
        expect(writes).toEqual([])
        await page.getByRole('button', { name: /^Continue$/ }).click()
        await expect(pause).toBeVisible()
        await page.reload()
        await expect(pause).toBeVisible()
        expect(await currentSession(request)).toEqual(before)
        if (phase === 'teach') await expect(page.getByLabel('Ask about this lesson (optional)')).toHaveValue('Keep this unfinished question.')
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
        await page.screenshot({ path: info.outputPath('resumed.png'), fullPage: true })
        await page.getByRole('button', { name: 'End session', exact: true }).click()
        await expect(page).toHaveURL(/\/$/)
        expect(await currentSession(request)).toBeNull()
        const ended = await (await request.get(`${API}/api/sessions/${session.id}`)).json()
        expect(ended.energy_after).toBeNull()
      } finally {
        await endOpenSession(request)
      }
    })
  }
}

for (const step of ['start', 'movement-next', 'review-next'] as const) {
  test(`late ${step} response cannot undo pause`, async ({ page, request }) => {
    await endOpenSession(request)
    try {
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      if (step !== 'start') {
        const type = step === 'movement-next' ? 'movement_primer' : 'retrieval'
        const index = session.plan.findIndex((block: { type: string }) => block.type === type)
        expect(index).toBeGreaterThanOrEqual(0)
        await expectOk(await request.post(`${API}/api/plan/blocks/start`, {
          data: { session_id: session.id, index },
        }))
      }
      await page.goto('/')
      await page.getByRole('button', { name: /^Continue$/ }).click()
      if (step === 'review-next') await finishReview(page)
      let release!: () => void
      const delivery = new Promise<void>((resolve) => { release = resolve })
      let committed!: () => void
      const ready = new Promise<void>((resolve) => { committed = resolve })
      let delivered!: () => void
      const finished = new Promise<void>((resolve) => { delivered = resolve })
      await page.route(`**/api/plan/blocks/${step === 'start' ? 'start' : 'next'}`, async (route) => {
        const saved = await route.fetch()
        await expectOk(saved)
        committed()
        await delivery
        await route.fulfill({ response: saved })
        delivered()
      })
      const action = step === 'start' ? /then new material/ : step === 'movement-next' ? 'Skip this block' : 'Continue the plan'
      await page.getByRole('button', { name: action }).click()
      await ready
      await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
      await expect(page).toHaveURL(/\/$/)
      release()
      await finished
      // Allow the intentionally delayed response callbacks to run before checking navigation.
      await page.waitForTimeout(200)
      // A read of the fresh server state on Home must settle without old navigation winning.
      await expect(page.getByRole('button', { name: /^Continue$/ })).toBeVisible()
      await expect.poll(() => page.url()).toMatch(/\/$/)
      const persisted = await currentSession(request)
      expect(persisted?.id).toBe(session.id)
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await expect(page.getByRole('button', { name: 'Pause and return Home', exact: true })).toBeVisible()
      expect(await currentSession(request)).toEqual(persisted)
    } finally {
      await endOpenSession(request)
    }
  })
}
