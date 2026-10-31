import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'
import axe from 'axe-core'

test('maintenance preference is explicit, reversible and does not replace a running plan', async ({
  page,
  request,
}) => {
  await endOpenSession(request)
  const before = (await (await request.get(`${API}/api/preferences`)).json()).values['planner.maintenance']
  try {
    const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(started)
    const session = await started.json()
    await page.setViewportSize({ width: 390, height: 900 })
    await page.goto('/preferences')
    await page
      .getByRole('switch', { name: 'Maintenance plans: brief recall and recap only (new sessions)' })
      .click()
    await expect
      .poll(
        async () =>
          (await (await request.get(`${API}/api/preferences`)).json()).values['planner.maintenance'],
      )
      .toBe(true)
    const preview = await (await request.get(`${API}/api/plan/preview?mode=novelty&energy=5`)).json()
    expect(preview.blocks.map((b: { type: string }) => b.type)).toEqual(['retrieval', 'recap'])
    const selection = await request.get(`${API}/api/sessions/selection/selected-lesson`)
  expect(selection.status()).toBe(409)
  expect((await selection.json()).error.code).toBe('maintenance_planning')
  const still = await (await request.get(`${API}/api/sessions/${session.id}`)).json()
    expect(still.plan).toEqual(session.plan)
    await page.reload()
    await expect(
      page.getByRole('switch', { name: 'Maintenance plans: brief recall and recap only (new sessions)' }),
    ).toBeChecked()
    await page
      .getByRole('switch', { name: 'Maintenance plans: brief recall and recap only (new sessions)' })
      .click()
    await expect
      .poll(
        async () =>
          (await (await request.get(`${API}/api/preferences`)).json()).values['planner.maintenance'],
      )
      .toBe(false)
  } finally {
    await request.put(`${API}/api/preferences`, { data: { key: 'planner.maintenance', value: before } })
    await endOpenSession(request)
  }
})

test('next-start cue saves explicitly, survives Home reload and clears without touching recap', async ({
  page,
  request,
}) => {
  const before = (await (await request.get(`${API}/api/preferences`)).json()).values['session.next_start_cue']
  try {
    await page.goto('/preferences')
    await page.getByLabel('If-then starting cue (optional)').fill('After tea, recall one saved question.')
    await page.getByRole('button', { name: 'Save next-start cue', exact: true }).click()
    await expect(page.getByText('Next-start cue saved for Home.', { exact: true })).toBeVisible()
    await page.goto('/')
    await expect(page.getByRole('complementary', { name: 'Next-start cue' })).toContainText(
      'After tea, recall one saved question.',
    )
    await page.reload()
    await expect(page.getByRole('complementary', { name: 'Next-start cue' })).toContainText(
      'After tea, recall one saved question.',
    )
    await page.goto('/preferences')
    await page.getByLabel('If-then starting cue (optional)').fill('')
    await page.getByRole('button', { name: 'Clear next-start cue', exact: true }).click()
    await expect(page.getByText('Next-start cue cleared.', { exact: true })).toBeVisible()
    await page.goto('/')
    await expect(page.getByRole('complementary', { name: 'Next-start cue' })).toHaveCount(0)
    await page.goto('/experiments')
    await page.getByText('Study conditions and later recall (optional)', { exact: true }).click()
    await expect(
      page.getByText('No qualifying later recall yet. Nothing is ranked or recommended.', { exact: true }),
    ).toBeVisible()
    await page.addScriptTag({ content: axe.source })
    expect(
      await page.evaluate(
        async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations,
      ),
    ).toEqual([])
  } finally {
    await request.put(`${API}/api/preferences`, { data: { key: 'session.next_start_cue', value: before } })
  }
})
