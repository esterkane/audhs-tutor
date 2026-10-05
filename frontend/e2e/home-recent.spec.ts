import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`Home returns to recently browsed areas without learning writes ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() =>
      sessionStorage.setItem(
        'audhs-browse-areas:v1',
        JSON.stringify({ version: 1, current: 'python', recent: ['python', 'gone', 'audio'] }),
      ),
    )
    const writes: string[] = []
    const reviewReads: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/') && request.method() !== 'GET') writes.push(request.url())
      if (request.url().includes('/api/review/due')) reviewReads.push(request.url())
    })
    await page.route('**/api/areas', (route) =>
      route.fulfill({
        json: {
          areas: ['python', 'audio'].map((id) => ({
            id,
            title: id,
            terms: [],
            courses: [],
            documents: 0,
            related: [],
            description: '',
          })),
          total_documents: 0,
          unassigned_documents: 0,
        },
      }),
    )
    await page.route('**/api/sessions/current', (route) =>
      route.fulfill({
        json: {
          id: 'fixture',
          active_skill: { id: 'lesson', title: 'Comparing groups' },
          due_reviews: 100,
          state: { skill_id: 'lesson', block_status: 'running', phase: 'teach', plan_complete: false },
        },
      }),
    )
    await page.goto('/')
    if (
      (await page
        .getByText('Recently opened material', { exact: true })
        .locator('..')
        .getAttribute('open')) === null
    )
      await page.getByText('Recently opened material', { exact: true }).click()
    const recent = page.getByRole('region', { name: 'Recently browsed areas' })
    await expect(recent.getByRole('link', { name: 'python', exact: true })).toBeVisible()
    await expect(recent.getByText(/previously visited area is unavailable/)).toBeVisible()
    await expect(page.getByText('At least 100 reviews are due for this saved session.')).toBeVisible()
    await expect(page.getByRole('button', { name: /^Continue$/ })).toBeVisible()
    await page.screenshot({ path: info.outputPath('home-recent.png'), fullPage: true })
    await recent.getByRole('link', { name: 'audio', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/areas\?area=audio$/)
    await page.goBack()
    if (
      (await page
        .getByText('Recently opened material', { exact: true })
        .locator('..')
        .getAttribute('open')) === null
    )
      await page.getByText('Recently opened material', { exact: true }).click()
    await expect(recent.getByRole('link', { name: 'audio', exact: true })).toBeVisible()
    await page.reload()
    if (
      (await page
        .getByText('Recently opened material', { exact: true })
        .locator('..')
        .getAttribute('open')) === null
    )
      await page.getByText('Recently opened material', { exact: true }).click()
    await expect(recent.getByRole('link', { name: 'audio', exact: true })).toBeVisible()
    expect(writes).toEqual([])
    expect(reviewReads).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}

test('recent area lookup failure offers retry without inventing reviews or stale links', async ({
  page,
}, info) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.addInitScript(() =>
    sessionStorage.setItem(
      'audhs-browse-areas:v1',
      JSON.stringify({ version: 1, current: 'python', recent: ['python'] }),
    ),
  )
  let unavailable = true
  await page.route('**/api/areas', (route) =>
    unavailable
      ? route.fulfill({ status: 503, json: { detail: 'Fixture unavailable' } })
      : route.fulfill({
          json: {
            areas: [
              {
                id: 'python',
                title: 'Understanding local inference and responsible machine learning applications',
                terms: [],
                courses: [],
                documents: 0,
                related: [],
                description: '',
              },
            ],
          },
        }),
  )
  await page.route('**/api/sessions/current', (route) => route.fulfill({ json: null }))
  await page.goto('/')
  if (
    (await page.getByText('Recently opened material', { exact: true }).locator('..').getAttribute('open')) ===
    null
  )
    await page.getByText('Recently opened material', { exact: true }).click()
  const recent = page.getByRole('region', { name: 'Recently browsed areas' })
  await expect(recent.getByRole('button', { name: 'Retry recent areas' })).toBeVisible()
  await expect(recent.getByRole('link', { name: 'python', exact: true })).toHaveCount(0)
  await expect(page.getByText(/reviews are due for this saved session/)).toHaveCount(0)
  unavailable = false
  await recent.getByRole('button', { name: 'Retry recent areas' }).click()
  await expect(recent.getByRole('link', { name: /Understanding local inference/ })).toBeVisible()
  await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
  await page.getByText('Session options', { exact: true }).click()
  await page.getByText(/More options · questioning style:/).click()
  const mode = page.getByRole('group', { name: 'State mode', exact: true })
  const low = mode.getByRole('button', { name: /^Low capacity/ })
  await low.focus()
  await page.keyboard.press('Enter')
  await expect(low).toHaveAttribute('aria-pressed', 'true')
  await expect(mode.getByRole('button')).toHaveCount(3)
  await page.evaluate(() => document.fonts.ready)
  await mode.screenshot({ path: info.outputPath('mode-options-zoom.png') })
  await page.screenshot({ path: info.outputPath('recent-long-title-zoom.png'), fullPage: true })
  const overflow = await page.evaluate(() =>
    [...document.querySelectorAll('body *')]
      .filter((el) => {
        const rect = el.getBoundingClientRect()
        return el.checkVisibility() && rect.width > 0 && rect.right > innerWidth + 1
      })
      .map((el) => ({
        tag: el.tagName,
        text: el.textContent?.slice(0, 100),
        className: el.className,
        right: el.getBoundingClientRect().right,
      })),
  )
  expect(overflow).toEqual([])
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
