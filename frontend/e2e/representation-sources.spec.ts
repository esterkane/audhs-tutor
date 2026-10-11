import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const narrow of [false, true]) {
  test(`representation historical sources ${narrow ? 'narrow' : 'desktop'}`, async ({ page, request }, info) => {
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
          json: { kinds: [{ kind: 'analogy', label: 'Analogy', allowed: true, cached: true }, { kind: 'worked_example', label: 'Worked example', allowed: true, cached: false }] },
        }),
      )
      await page.route('**/api/answers/recover-save', route => route.fulfill({ json: { answer_id: 'recovered-representation' } }))
      let exampleCalls = 0
      await page.route('**/api/objects/*/representations/worked_example', async route => {
        exampleCalls += 1
        await new Promise(resolve => setTimeout(resolve, 250))
        if (exampleCalls === 1) {
          await route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Example temporarily unavailable' } } })
        } else {
          await route.fulfill({ json: {
            object_id: 'fixture', skill_id: session.next_skill.id, concept: 'Comparison',
            kind: 'worked_example', content: 'Worked example: compare two matching components.',
            representation_id: 'example', cached: false, answer_id: 'saved-example',
            provenance_available: true, sources: [], source_snapshot: [], source_text_hashes: {},
          } })
        }
      })
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
            answer_id: legacy ? null : 'saved-representation',
            save_error: legacy ? 'Could not save this explanation.' : null,
            save_receipt: legacy ? 'signed-fixture' : null,
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
      await page.getByRole('button', { name: /^Continue$/ }).click()
      await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
      const draft = page.getByLabel('Ask about this lesson (optional)')
      await draft.fill('Keep my unsent question')
      await page.getByRole('button', { name: 'Give me an example', exact: true }).evaluate(el => {
        (el as HTMLButtonElement).click(); (el as HTMLButtonElement).click()
      })
      await expect(page.getByRole('alert').filter({ hasText: 'Example temporarily unavailable' })).toBeVisible()
      expect(exampleCalls).toBe(1)
      await expect(draft).toHaveValue('Keep my unsent question')
      await expect(page.getByRole('region', { name: 'Explanation reader' })).toContainText('Compare matching components.')
      await page.getByRole('button', { name: 'Give me an example', exact: true }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Worked example: compare two matching components.', { exact: true })).toBeVisible()
      await expect(draft).toHaveValue('Keep my unsent question')
      expect(exampleCalls).toBe(2)
      const differently = page.getByRole('button', { name: 'Explain differently', exact: true })
      await differently.focus()
      await page.keyboard.press('Enter')
      await expect(differently).toHaveAttribute('aria-expanded', 'true')
      await expect(page.getByRole('button', { name: 'Let me try', exact: true })).toBeEnabled()
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(narrow ? 390 : 1280)
      await page.screenshot({ path: info.outputPath('tutoring-actions.png'), fullPage: true })
      await page.getByRole('group', { name: 'Show it differently', exact: true }).getByRole('button', { name: 'Analogy', exact: false }).click()
      await expect(page.getByRole('link', { name: 'Open saved answer', exact: true })).toHaveAttribute('href', '/answers/saved-representation')
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
      await page.getByRole('group', { name: 'Show it differently', exact: true }).getByRole('button', { name: 'Analogy', exact: false }).click()
      await expect(page.getByText(/Original source details were not recorded/)).toBeVisible()
      await expect(citation).toHaveCount(0)
      await page.getByRole('button', { name: 'Retry saving', exact: true }).click()
      await expect(page.getByRole('link', { name: 'Open saved answer', exact: true })).toHaveAttribute('href', '/answers/recovered-representation')
    } finally {
      await endOpenSession(request)
    }
  })
}
