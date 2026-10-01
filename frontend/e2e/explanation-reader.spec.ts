import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

test('completed explanation sections preserve notes, focus and optional follow-up', async ({
  page,
  request,
}) => {
  await endOpenSession(request)
  try {
    await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
    await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
    const res = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(res)
    const session = await res.json()
    const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
    await expectOk(
      await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }),
    )
    const text =
      '## The idea\nCompare matching components.\n\n## A worked example\nAn illustrative pair gives 2 × 3 = 6.\n\n## Try one step\nPredict what doubling one component changes.'
    let calls = 0
    let release: (() => void) | undefined
    await page.route('**/api/tutor/stream', async (route) => {
      calls += 1
      await new Promise<void>((resolve) => {
        release = resolve
      })
      return route.fulfill({
        contentType: 'text/event-stream',
        body: `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ turn_id: 'reader-fixture', sources: [], outcome: 'ok', text })}\n\n`,
      })
    })
    await page.goto('/')
    await page.getByRole('button', { name: /^Resume previous session/ }).click()
    await page.getByRole('button', { name: 'Start explanation', exact: true }).click()
    await expect(page.getByRole('status', { name: 'Tutor response status' })).toContainText('preparing')
    await expect(page.getByText(/Waiting [1-9]\d* seconds?/)).toBeVisible()
    release!()
    await expect(page.getByRole('status', { name: 'Tutor response status' })).toHaveText(
      'Tutor response ready.',
    )
    await expect(page.getByRole('heading', { name: 'Section 1 of 3: The idea' })).toBeVisible()
    await page.getByRole('button', { name: 'Next section', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Section 2 of 3: A worked example' })).toBeFocused()
    await page
      .getByRole('textbox', { name: 'Your notes for this section (optional)' })
      .fill('Check what changes when doubled.')
    await page.getByRole('button', { name: 'Previous section', exact: true }).click()
    await page.getByRole('button', { name: 'Next section', exact: true }).click()
    await expect(page.getByRole('textbox', { name: 'Your notes for this section (optional)' })).toHaveValue(
      'Check what changes when doubled.',
    )
    await page.getByRole('radio', { name: 'Full explanation', exact: true }).check()
    await expect(
      page
        .getByRole('region', { name: 'Explanation reader' })
        .getByText('Compare matching components.', { exact: true }),
    ).toBeVisible()
    await expect(
      page
        .getByRole('region', { name: 'Explanation reader' })
        .getByText('Predict what doubling one component changes.', { exact: true }),
    ).toBeVisible()
    await page.getByText('Think deeper about this explanation', { exact: true }).click()
    await page.getByRole('button', { name: 'Find a counterexample', exact: true }).click()
    expect(
      await page.getByRole('textbox', { name: 'Ask about this lesson (optional)' }).inputValue(),
    ).toContain('Compare matching components.')
    expect(calls).toBe(1)
    await page.getByRole('button', { name: 'Stop session', exact: true }).click()
  } finally {
    await endOpenSession(request)
  }
})
