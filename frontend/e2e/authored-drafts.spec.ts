import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [1280, 390]) {
  test(`course-independent drafts can be reviewed without activation at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const draft = {
      id: 'authored-draft', course: null, section: null, title: 'Training-only preprocessing',
      status: 'draft', origin: 'authored', version: 1, problems: [],
      payload: { domain: 'ai_ml', skills: [], learning_objects: [], assessments: [] },
      created_at: 'now', updated_at: 'now', published_at: null,
    }
    let writes = 0
    let failed = true
    await page.route('**/api/curriculum/**', route => {
      if (route.request().method() !== 'GET') { writes++; return route.fulfill({ status: 500, body: '' }) }
      const url = new URL(route.request().url())
      if (url.pathname.endsWith('/material')) return route.fulfill({ json: { courses: [] } })
      if (url.pathname.endsWith('/drafts')) return failed
        ? route.fulfill({ status: 503, json: { error: { message: 'Temporarily unavailable' } } })
        : route.fulfill({ json: { drafts: [draft] } })
      return route.continue()
    })
    await page.goto('/curriculum')
    await expect(page.getByRole('button', { name: 'Retry drafts' })).toBeVisible()
    failed = false
    await page.getByRole('button', { name: 'Retry drafts' }).click()
    const review = page.getByRole('button', { name: 'Review Training-only preprocessing' })
    await expect(review).toBeVisible()
    await review.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: draft.title, exact: true })).toBeFocused()
    await expect(page.getByRole('button', { name: 'Back to drafts' })).toBeVisible()
    await page.getByRole('button', { name: 'Back to drafts' }).focus()
    await page.keyboard.press('Enter')
    await expect(review).toBeVisible()
    await page.reload()
    await expect(review).toBeVisible()
    expect(writes).toBe(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    await page.screenshot({ path: `/tmp/audhs-authored-drafts-${width}.png` })
  })
}
