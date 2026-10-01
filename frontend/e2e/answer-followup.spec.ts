import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`saved follow-up sends explicitly and retains lineage (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'session' } }))
    let feedback = { verdict: null as string | null, note: '', hidden: false, revision: 0 }
    await page.route('**/api/answers/*/feedback', async (route) => {
      if (route.request().method() === 'PUT')
        feedback = { ...route.request().postDataJSON(), revision: feedback.revision + 1 }
      await route.fulfill({ json: feedback })
    })
    const parent = {
      id: 'parent',
      text: 'Compare group representation.',
      request_text: 'Why compare?',
      request: {},
      metadata: {},
      created_at: '2026-10-01T10:00:00Z',
    }
    await page.route('**/api/answers/parent', (route) => route.fulfill({ json: parent }))
    let calls = 0
    await page.route('**/api/answers/parent/followup', async (route) => {
      calls++
      expect(route.request().postDataJSON()).toEqual({
        session_id: 'session',
        question: 'Show a small example.',
      })
      await route.fulfill({ json: { text: 'Illustrative: compare 9/10 with 6/10.', answer_id: 'child' } })
    })
    await page.route('**/api/answers/child', (route) =>
      route.fulfill({
        json: {
          ...parent,
          id: 'child',
          text: 'Illustrative: compare 9/10 with 6/10.',
          request_text: 'Show a small example.',
          request: { historical_answer: { answer: parent.text, truncated_fields: [] } },
          metadata: { parent_answer_id: 'parent' },
        },
      }),
    )
    await page.goto('/answers/parent')
    await page.getByRole('combobox', { name: 'How was this answer?' }).selectOption('incorrect')
    await page.getByRole('textbox', { name: 'Why? (optional)' }).fill('Check the totals')
    await page.getByRole('button', { name: 'Save feedback', exact: true }).click()
    await expect(page.getByText('Feedback saved.')).toBeVisible()
    await expect(page.getByText(/The reply you will continue from is marked incorrect/)).toBeVisible()
    const input = page.getByRole('textbox', { name: 'Your follow-up question' })
    await expect(input).toBeVisible()
    expect(calls).toBe(0)
    await input.fill('Show a small example.')
    await page.getByRole('button', { name: 'Send follow-up' }).click()
    await expect(page.getByText('Illustrative: compare 9/10 with 6/10.')).toBeVisible()
    expect(calls).toBe(1)
    await page.getByRole('link', { name: 'Open saved follow-up' }).click()
    await expect(page.getByRole('link', { name: 'previous saved answer' })).toHaveAttribute(
      'href',
      '/answers/parent',
    )
    await page.getByText('Historical context supplied for this reply').click()
    await expect(page.getByText(/Compare group representation/)).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole('link', { name: 'previous saved answer' }).click()
    await expect(page.getByRole('link', { name: 'latest saved follow-up' })).toHaveAttribute(
      'href',
      '/answers/child',
    )
  })
}
