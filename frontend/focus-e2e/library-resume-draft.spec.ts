import { expect, test } from '@playwright/test'
import { API, expectOk } from '../e2e/helpers'

test('Library keeps editable work reachable after newer drafts were discarded', async ({ page, request }) => {
  async function create(title: string) {
    const response = await request.post(API + '/api/knowledge-material/drafts', {
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      data: {
        title,
        focus_topic: 'postgresql',
        domain: 'programming',
        notes: 'Synthetic personal notes on SQL privileges.',
        workflow_step: 'source',
      },
    })
    await expectOk(response)
    return response.json()
  }
  const title = 'Synthetic permission diary'
  const editable = await create(title)
  for (let i = 0; i < 5; i++) {
    const inactive = await create('Archived scratch example ' + i)
    await expectOk(
      await request.post(API + '/api/curriculum/drafts/' + inactive.id + '/reject', {
        data: { expected_version: inactive.version },
      }),
    )
  }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/library')
  const recent = page.getByRole('region', { name: 'Recent material' })
  await expect(recent.getByRole('link', { name: title })).toBeVisible()
  await expect(recent.getByRole('link', { name: /Archived scratch/ })).toHaveCount(0)
  await recent.getByRole('link', { name: title }).press('Enter')
  await expect(page).toHaveURL(new RegExp('draft=' + editable.id))
  const notes = page.getByRole('textbox', { name: 'Your notes and selected source content' })
  const unsaved = 'I am comparing read grants against row policies. This paragraph is still a draft.'
  await notes.fill(unsaved)
  await page
    .getByRole('navigation', { name: 'Main navigation' })
    .getByRole('link', { name: 'Library', exact: true })
    .click()
  await page.getByRole('searchbox', { name: 'Search phrase' }).fill(title)
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await page.getByRole('region', { name: 'My material' }).getByRole('link', { name: title }).press('Enter')
  await expect(notes).toHaveValue(unsaved)
  await page.reload()
  await expect(notes).toHaveValue(unsaved)
  const saving = page.waitForResponse(
    (r) => r.url().endsWith('/drafts/' + editable.id) && r.request().method() === 'PUT',
  )
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expectOk(await saving)
})
