import { expect, test } from '@playwright/test'

for (const width of [320, 1280]) test(`Task review is explicit and recoverable ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  let writes = 0
  await page.route('**/api/questions/example/task-review', async route => {
    if (route.request().method() === 'POST') {
      writes++
      await route.fulfill({ json: { decision: 'approve' } })
    } else await route.fulfill({ json: { assessment_id: 'example', content_version: 'version', current_review: null, approval_matches_content: false, reviewable: true, unavailable_reason: null,
      content: { objective: { title: 'Explain selection bias', description: 'Explain why removing incomplete rows changes who is represented.' }, item: { prompt: 'Who could be excluded when missing rows are removed?' }, criteria: [{ criterion: 'Identify an excluded group and explain a consequence' }] } } })
  })
  await page.goto('/task-review?assessment=example&returnTo=%2Flearn')
  await expect(page.getByText('Who could be excluded when missing rows are removed?')).toHaveCount(0)
  const reveal = page.getByRole('button', { name: 'Show task and rubric' })
  await reveal.focus(); await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Content to review' })).toBeFocused()
  const approve = page.getByRole('button', { name: 'Approve this task review' })
  await expect(approve).toBeDisabled()
  await page.getByRole('checkbox').focus(); await page.keyboard.press('Space')
  await expect(approve).toBeEnabled()
  await page.screenshot({ path: info.outputPath(`review-${width}.png`), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await approve.focus(); await page.keyboard.press('Enter')
  const saved = page.getByText('Task review saved. This does not change your grades or confirm understanding.')
  await expect(saved).toBeFocused()
  expect(writes).toBe(1)
  await expect(page.getByRole('link', { name: 'Return to previous activity' })).toHaveAttribute('href', '/learn')
})

test('A held review save does not steal focus from the return link', async ({ page }) => {
  let release!: () => void
  const held = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/questions/example/task-review', async route => {
    if (route.request().method() === 'POST') {
      await held
      await route.fulfill({ json: { decision: 'approve' } })
    } else await route.fulfill({ json: { assessment_id: 'example', content_version: 'v1', current_review: null, approval_matches_content: false, reviewable: true, content: { objective: {}, item: { prompt: 'Example' }, criteria: [] } } })
  })
  await page.goto('/task-review?assessment=example&returnTo=%2Flearn')
  await page.getByRole('button', { name: 'Show task and rubric' }).click()
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Approve this task review' }).click()
  const back = page.getByRole('link', { name: 'Return to previous activity' })
  await back.focus(); release()
  await expect(page.getByText('Task review saved. This does not change your grades or confirm understanding.')).toBeVisible()
  await expect(back).toBeFocused()
})
