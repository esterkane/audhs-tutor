import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`saved answer keyboard round trip (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 })
    const requests: string[] = []
    page.on('request', (request) => {
      if (request.method() === 'POST') requests.push(request.url())
    })
    const item = {
      id: 'saved-one',
      request_text: 'Why compare groups?',
      preview: 'Representation may change.',
      surface: 'playground',
      created_at: '2026-10-01T10:00:00Z',
    }
    await page.route('**/api/answers?*', (route) =>
      route.fulfill({ json: { items: [item], next_cursor: null } }),
    )
    await page.route('**/api/answers/saved-one', (route) =>
      route.fulfill({
        json: {
          ...item,
          text: 'Compare representation before and after cleaning.',
          request: {
            code: 'print(groups)',
            history: [{ role: 'user', text: 'What changed after cleaning?' }],
          },
          metadata: {},
          turn_id: 'saved-turn',
        },
      }),
    )
    await page.route('**/api/answers/saved-one/source-status', (route) =>
      route.fulfill({ json: { sources: [{ chunk_id: 'source-one', status: 'changed', newer_version: true }], omitted: 0 } }),
    )
    await page.goto('/answers?surface=playground')
    await page.getByRole('searchbox', { name: 'Search saved answers' }).fill('groups')
    await page.getByRole('button', { name: 'Search', exact: true }).click()
    await expect(page).toHaveURL(/q=groups/)
    const answer = page.getByRole('link', { name: 'Why compare groups?' })
    await expect(answer).toHaveAttribute('href', /q=groups/)
    await answer.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Compare representation before and after cleaning.')).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Saved answer', exact: true })).toBeFocused()
    await page.getByRole('button', { name: 'Check saved source text' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText(/Source text has changed/)).toBeVisible()
    await expect(page.getByText(/a newer local document version exists/)).toBeVisible()
    await page.getByText('Conversation supplied at the time').click()
    await expect(page.getByText('What changed after cleaning?')).toBeVisible()
    await page.getByText('Material and code supplied at the time').click()
    await expect(page.getByText('print(groups)')).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole('link', { name: 'Back to saved answers' }).click()
    await expect(page.getByRole('combobox', { name: 'Show', exact: true })).toHaveValue('playground')
    await expect(page.getByRole('searchbox', { name: 'Search saved answers' })).toHaveValue('groups')
    await page.getByRole('button', { name: 'Clear search' }).click()
    await expect(page).not.toHaveURL(/q=/)
    expect(requests.filter((url) => /tutor|assess|sessions/.test(url))).toEqual([])
  })
}
