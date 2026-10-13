import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`listening cloze draft stays with its question ${width}`, async ({ page }) => {
    let changed = false
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/listening/lessons/clip', route => route.fulfill({ json: {
      document_id: 'clip', title: 'Synthetic clip', media_url: null, language: 'en', next_index: 0,
      sections: [{ chunk_id: 'chunk', t_start: 0, t_end: 20, text: 'Synthetic transcript', index: 0 }],
    } }))
    await page.route('**/api/listening/lessons/clip/sections/0/task', route => route.fulfill({ json: {
      item: { id: 'draft-fixture', skill_id: 'fixture', kind: 'cloze', question: changed ? 'New missing word ____.' : 'Old missing word ____.', content_version: changed ? 'two' : 'one', options: null, criteria: null, confidence_required: false },
      origin: 'deterministic', validated: true, problems: [], citation: null, clip: { t_start: 0, t_end: 20, chunk_id: 'chunk' },
    } }))
    async function mount() {
      await page.goto('/')
      await page.evaluate(() => {
        const el = document.createElement('div'); el.id = 'fixture'; el.dataset.sessionId = 'draft-session'; el.className = 'm-4'; document.body.append(el)
      })
      await page.addScriptTag({ type: 'module', url: '/src/test/browser/listening-coordination.tsx' })
      await page.locator('#fixture').getByRole('button', { name: 'I have read it — go to the question' }).click()
    }
    await mount()
    const fixture = page.locator('#fixture')
    await fixture.getByLabel('The missing word').fill('earlier answer')
    changed = true
    await mount()
    await expect(fixture.getByLabel('The missing word')).toHaveValue('')
    await expect(fixture.getByRole('button', { name: 'Check', exact: true })).toBeDisabled()
    await fixture.locator('summary').filter({ hasText: 'Earlier answer drafts' }).focus()
    await page.keyboard.press('Enter')
    await expect(fixture.getByText('earlier answer', { exact: true })).toBeVisible()
    await fixture.getByLabel('The missing word').fill('new answer')
    await mount()
    await expect(fixture.getByLabel('The missing word')).toHaveValue('new answer')
    await fixture.locator('summary').filter({ hasText: 'Earlier answer drafts' }).click()
    await expect(fixture.getByText('earlier answer', { exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await fixture.screenshot({ path: `/tmp/listening-draft-${width}.png` })
  })
}
