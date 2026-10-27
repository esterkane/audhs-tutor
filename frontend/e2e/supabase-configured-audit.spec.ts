import { test, expect } from '@playwright/test'
import axe from 'axe-core'
import { API_URL } from '../playwright.config'
test.skip(
  process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Opt-in: requires an isolated configured local project stack',
)
test('real local incident response, protected learner findings, reload, project evidence and authoring handoff', async ({
  page,
  request,
}) => {
  await page.goto('/projects/supabase')
  await page.getByRole('button', { name: /Explicit \(default\)/ }).click()
  const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
  await input.fill(
    'Our SELECT fails: permission denied for table orders. A row policy exists. Explain the difference between missing grants and no rows.',
  )
  const done = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  expect((await done).ok()).toBeTruthy()
  await expect(page.getByText(/The reported table permission error concerns/)).toBeVisible()
  await expect(page.getByText(/has_table_privilege\(current_user, c.oid/)).toBeVisible()
  const sessionId = await page.evaluate(
    () =>
      Object.keys(localStorage)
        .filter((k) => k.startsWith('kaenguru.session.'))
        .map((k) => localStorage.getItem(k))[0],
  )
  expect(sessionId).toBeTruthy()
  const edit = await request.patch(API_URL + '/api/supabase-project/session/' + sessionId + '/incident', {
    data: {
      field: 'root_cause',
      value: 'Learner hypothesis, not established: compare effective role grants.',
    },
  })
  expect(edit.ok()).toBeTruthy()
  await page.reload()
  await expect(page.getByText(/The reported table permission error concerns/)).toBeVisible()
  await input.fill('Our request fails: permission denied for schema customer_data.')
  const second = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  expect((await second).ok()).toBeTruthy()
  await expect(page.getByText(/The reported schema permission error points/)).toBeVisible()
  const restored = await request.get(API_URL + '/api/supabase-project/session/' + sessionId)
  const saved = await restored.json()
  expect(saved.transcript).toHaveLength(4)
  expect(saved.incident.model.root_cause).toContain('Learner hypothesis')
  expect(saved.incident.sources.root_cause).toBe('learner')
  await page.setViewportSize({ width: 390, height: 900 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.addScriptTag({ content: axe.source })
  expect(
    await page.evaluate(
      async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations,
    ),
  ).toEqual([])
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Supabase', exact: true }).click()
  await page
    .getByRole('textbox', { name: 'My project notes', exact: true })
    .fill('Synthetic incident learning: privileges and row visibility are separate.')
  await page.getByRole('button', { name: 'Save project notes', exact: true }).click()
  await expect(page.getByRole('status')).toContainText('Project writing saved')
  await page.reload()
  await expect(page.getByRole('textbox', { name: 'My project notes', exact: true })).toHaveValue(
    /Synthetic incident learning/,
  )
  await page.getByRole('link', { name: 'Create knowledge material from notes or uploads' }).click()
  await expect(page.getByRole('heading', { name: 'Knowledge material', exact: true })).toBeVisible()
})
