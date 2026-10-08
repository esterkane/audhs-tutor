import { expect, test, type Page } from '@playwright/test'

async function openDraft(page: Page) {
  await page.getByLabel('Course', { exact: true }).selectOption('Synthetic material')
  await page.getByRole('button', { name: 'Review One section' }).click()
}

for (const width of [1280, 390]) {
  test(`draft reload preserves partial edits and server conflict at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    const original = {
      id: 'reload-draft', course: 'Synthetic material', section: 'One section', title: 'Draft',
      status: 'draft', origin: 'deterministic', version: 1, problems: [],
      payload: { domain: 'ai_ml', skills: [], learning_objects: [], assessments: [] },
      created_at: 'now', updated_at: 'now', published_at: null,
    }
    let latest = original
    let writes = 0
    await page.route('**/api/curriculum/**', (route) => {
      const url = new URL(route.request().url())
      if (route.request().method() !== 'GET') {
        writes++
        return route.fulfill({ status: 500, json: { error: { code: 'unexpected', message: 'No automatic writes allowed' } } })
      }
      if (url.pathname.endsWith('/material')) return route.fulfill({ json: { courses: [{ course: original.course, documents: 1, chunks: 1, drafts: 1, published_skills: 0, status: 'draft' }] } })
      if (url.pathname.endsWith('/sections')) return route.fulfill({ json: { course: original.course, sections: [] } })
      if (url.pathname.endsWith('/drafts')) return route.fulfill({ json: { drafts: [latest] } })
      if (url.pathname.includes('/drafts/')) return route.fulfill({ json: latest })
      return route.continue()
    })
    await page.goto('/curriculum')
    await openDraft(page)
    await page.getByText('Advanced: edit draft data', { exact: true }).click()
    const input = page.getByLabel('Draft JSON')
    await input.fill('{ unfinished draft: keep this text')
    await page.reload()
    await openDraft(page)
    let show = page.getByRole('button', { name: 'Show recovered edits', exact: true })
    await expect(show).toBeVisible()
    await show.focus()
    await page.keyboard.press('Enter')
    await expect(input).toBeFocused()
    await expect(input).toHaveValue('{ unfinished draft: keep this text')
    await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeEnabled()
    latest = { ...original, version: 2, payload: { ...original.payload, domain: 'language' } }
    await page.reload()
    await openDraft(page)
    show = page.getByRole('button', { name: 'Show recovered edits', exact: true })
    await show.focus()
    await page.keyboard.press('Enter')
    await expect(input).toHaveValue('{ unfinished draft: keep this text')
    await expect(page.getByRole('button', { name: 'Save changes', exact: true })).toBeDisabled()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true)
    await page.getByRole('heading', { name: 'One section', exact: true }).locator('..').screenshot({ path: `/tmp/draft-reload-${width}.png` })
    const discard = page.getByRole('button', { name: 'Discard unsaved edits', exact: true })
    await discard.focus()
    await page.keyboard.press('Enter')
    await expect(input).toHaveValue(JSON.stringify(latest.payload, null, 2))
    await page.reload()
    await openDraft(page)
    await expect(show).toHaveCount(0)
    expect(writes).toBe(0)
  })
}
