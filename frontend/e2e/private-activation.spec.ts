import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [1280, 390]) {
  test(`private activation review and interrupted recovery at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const draft = { id: 'private-draft', course: null, section: null, title: 'Fit on training data', status: 'draft', origin: 'answer_derived', version: 1, problems: [], created_at: 'now', updated_at: 'now', published_at: null,
      payload: { domain: 'ai_ml', skills: [{ slug: 'training', title: 'Training-only preprocessing', description: 'Apply a training statistic to held-out data.', prerequisites: [], success_criteria: ['Fit on training only'] }], learning_objects: [{ skill: 'training', concept: 'Fit and transform', goal: 'Protect held-out data.', examples: ['Training ages 20 and 40 give median 30. Apply 30 to both sets.'], exercises: ['Where should the imputation median come from?'], sources: [] }], assessments: [{ skill: 'training', kind: 'transfer', item: { prompt: 'Why not use the held-out ages?' }, rubric: [{ criterion: 'Keep held-out information out of fitting' }] }] } }
    const command = { promotion_id: 'promotion', expected_version: 1, payload_sha256: 'a'.repeat(64) }
    const receipt = { activation_id: 'receipt', promotion_id: 'promotion', draft_id: draft.id, activated_version: 1, payload_sha256: command.payload_sha256, skill_ids: ['skill'], object_ids: ['object'], assessment_ids: ['assessment'], edge_ids: [] }
    const posts: { body: unknown; key: string | undefined }[] = []
    let activated = false
    await page.route('**/api/curriculum/**', route => {
      const path = new URL(route.request().url()).pathname
      if (route.request().method() !== 'GET') throw new Error('Shared publication must not be used')
      if (path.endsWith('/material')) return route.fulfill({ json: { courses: [] } })
      const value = activated ? { ...draft, status: 'published', version: 2 } : draft
      if (path.endsWith('/drafts')) return route.fulfill({ json: { drafts: [value] } })
      return route.fulfill({ json: value })
    })
    await page.route('**/api/lesson-activations/**', route => {
      if (route.request().method() === 'POST') {
        posts.push({ body: route.request().postDataJSON(), key: route.request().headers()['idempotency-key'] })
        if (posts.length === 1) return route.abort('failed')
        activated = true
        return route.fulfill({ json: receipt })
      }
      return route.fulfill({ json: { draft_id: draft.id, promotion_id: 'promotion', draft_version: activated ? 2 : 1, title: draft.title, status: activated ? 'published' : 'draft', command: activated ? null : command, receipt: activated ? receipt : null, skills: activated ? 0 : 1, assessments: activated ? 0 : 1, learning_objects: activated ? 0 : 1, grounding: 'ungrounded', warnings: ['No source passages linked. Activation does not verify accuracy.'], issues: [] } })
    })
    await page.goto('/curriculum?draft=private-draft')
    const activate = page.getByRole('button', { name: 'Activate private lessons' })
    await expect(activate).toBeDisabled()
    const confirm = page.getByRole('checkbox', { name: /I reviewed this saved version/ })
    await confirm.focus(); await page.keyboard.press('Space')
    await expect(activate).toBeEnabled()
    await page.getByText('Source and review limitations', { exact: true }).click()
    await expect(page.getByText('No source passages linked. Activation does not verify accuracy.')).toBeVisible()
    await page.screenshot({ path: `/tmp/audhs-private-activation-review-${width}.png`, fullPage: true })
    await activate.focus(); await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Retry saved activation' })).toBeVisible()
    expect(posts).toHaveLength(1)
    await page.reload()
    const retry = page.getByRole('button', { name: 'Retry saved activation' })
    await expect(retry).toBeEnabled()
    expect(posts).toHaveLength(1)
    await retry.focus(); await page.keyboard.press('Enter')
    await expect(page.getByText('Your private lesson is active.', { exact: true })).toBeFocused()
    expect(posts).toHaveLength(2); expect(posts[1]).toEqual(posts[0])
    await page.reload()
    await expect(page.getByText('Your private lesson is active.', { exact: true })).toBeVisible()
    expect(posts).toHaveLength(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    await page.screenshot({ path: `/tmp/audhs-private-activation-after-${width}.png`, fullPage: true })
    await page.evaluate((narrow) => {
      document.documentElement.dataset.theme = 'dark'
      if (narrow) document.documentElement.style.fontSize = '200%'
      else document.body.style.zoom = '2'
    }, width === 390)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await expect(page.getByRole('link', { name: 'Choose a lesson on Home' })).toBeVisible()
    await page.screenshot({ path: `/tmp/audhs-private-activation-dark-zoom-${width}.png`, fullPage: true })
  })
}
