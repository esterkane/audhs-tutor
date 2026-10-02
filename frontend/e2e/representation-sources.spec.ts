import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const narrow of [false, true]) {
  test(`representation historical sources ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }) => {
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
      await page.route('**/api/tutor/stream', (route) =>
        route.fulfill({
          contentType: 'text/event-stream',
          body: 'event: done\ndata: {"turn_id":"fixture","text":"Compare matching components.","sources":[],"outcome":"ok"}\n\n',
        }),
      )
      await page.route('**/api/objects/*/representations', (route) =>
        route.fulfill({
          json: { kinds: [{ kind: 'analogy', label: 'Analogy', allowed: true, cached: true }] },
        }),
      )
      let legacy = false
      await page.route('**/api/objects/*/representations/analogy', (route) =>
        route.fulfill({
          json: {
            object_id: 'fixture',
            skill_id: session.next_skill.id,
            concept: 'Comparison',
            kind: 'analogy',
            content: 'A recorded analogy [1].',
            representation_id: legacy ? 'old' : 'recorded',
            cached: true,
            provenance_available: !legacy,
            sources: legacy ? [] : ['Original label'],
            source_snapshot: legacy
              ? []
              : [
                  {
                    chunk_id: 'recorded',
                    citation: 'Original label',
                    trust_tier: 1,
                    score: 1,
                    cited: true,
                    flagged: [],
                  },
                ],
            source_text_hashes: {},
          },
        }),
      )
      await page.route('**/api/corpus/chunks/recorded', (route) =>
        route.fulfill({ status: 404, json: { error: { code: 'not_found', message: 'Missing' } } }),
      )
      if (narrow) await page.setViewportSize({ width: 390, height: 844 })
      await page.goto('/')
      await page.getByRole('button', { name: /^Resume previous session/ }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      await page.getByText('Need another explanation or a different activity?', { exact: true }).click()
      await page.getByRole('button', { name: 'Analogy', exact: false }).click()
      const disclosure = page.getByText('Source context used for this explanation', { exact: true })
      await disclosure.focus()
      await page.keyboard.press('Enter')
      const citation = page.getByRole('button', { name: '[1] Original label', exact: true })
      await citation.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText(/This passage is no longer in the corpus/)).toBeVisible()
      await page.getByRole('button', { name: 'Close', exact: true }).click()
      await expect(citation).toBeFocused()
      legacy = true
      await page.getByRole('button', { name: 'Analogy', exact: false }).click()
      await expect(page.getByText(/Original source details were not recorded/)).toBeVisible()
      await expect(citation).toHaveCount(0)
    } finally {
      await endOpenSession(request)
    }
  })
}
