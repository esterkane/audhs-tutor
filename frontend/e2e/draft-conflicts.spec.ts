import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`stale draft keeps edits and explicitly loads latest at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const original = {
      id: 'synthetic-draft', course: 'Synthetic material', section: 'One section', title: 'Draft',
      status: 'draft', origin: 'deterministic', version: 1, problems: [],
      payload: { domain: 'ai_ml', skills: [], learning_objects: [], assessments: [] },
      created_at: 'now', updated_at: 'now', published_at: null,
    }
    let latest = original
    let writes = 0
    await page.route('**/api/curriculum/material', (route) => route.fulfill({ json: { courses: [{ course: original.course, documents: 1, chunks: 1, drafts: 1, published_skills: 0, status: 'draft' }] } }))
    await page.route('**/api/curriculum/sections?*', (route) => route.fulfill({ json: { course: original.course, sections: [] } }))
    await page.route('**/api/curriculum/drafts', (route) => route.fulfill({ json: { drafts: [latest] } }))
    await page.route('**/api/curriculum/drafts/synthetic-draft', (route) => {
      if (route.request().method() === 'PUT') {
        writes++
        expect(route.request().postDataJSON().expected_version).toBe(1)
        latest = { ...original, version: 2, payload: { ...original.payload, domain: 'language' } }
        return route.fulfill({ status: 409, json: { error: { code: 'draft_conflict', message: 'This draft changed elsewhere. Your edits have not been saved.' } } })
      }
      return route.fulfill({ json: latest })
    })
    await page.goto('/curriculum')
    await page.getByLabel('Course', { exact: true }).selectOption(original.course)
    await page.getByRole('button', { name: 'Review One section' }).click()
    await page.getByText('Advanced: edit draft data', { exact: true }).click()
    const input = page.getByLabel('Draft JSON')
    const edits = JSON.stringify({ ...original.payload, domain: 'music' })
    await input.fill(edits)
    await page.getByRole('button', { name: 'Save changes', exact: true }).click()
    const load = page.getByRole('button', { name: 'Load latest saved version', exact: true })
    await expect(load).toBeVisible()
    await expect(input).toHaveValue(edits)
    await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeDisabled()
    await load.focus()
    await expect(load).toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
    await page.screenshot({ path: `/tmp/draft-conflict-${width}.png`, fullPage: true })
    await page.keyboard.press('Enter')
    await expect(load).toHaveCount(0)
    await expect(input).toHaveValue(edits)
    const discard = page.getByRole('button', { name: 'Discard unsaved edits', exact: true })
    await discard.focus()
    await page.keyboard.press('Enter')
    await expect(input).toHaveValue(JSON.stringify(latest.payload, null, 2))
    expect(writes).toBe(1)
  })
}
