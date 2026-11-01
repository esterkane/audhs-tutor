import { test, expect } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1', 'Requires an isolated configured project')

test('failed outgoing question remains recoverable after reload without automatic resend', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/projects/supabase')
  await page.getByRole('button', { name: /Explicit/ }).click()
  const input = page.getByRole('textbox', { name: /message|question/i }).last()
  const question =
    'Synthetic interrupted research question: how do row policies differ from grants? https://reference.invalid/' +
    'x'.repeat(100)
  let attempted = 0
  await page.route('**/api/supabase-project/turn', (route) => {
    attempted++
    return route.abort('failed')
  })
  await input.fill(question)
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  await expect(page.getByRole('alert')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Saved question awaiting an answer', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Restore question to editor', exact: true }).click()
  await expect(input).toHaveValue(question)
  expect(attempted).toBe(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.reload()
  await expect(input).toHaveValue(question)
  expect(attempted).toBe(1)
})

test('completed question clears recovery state while new notes and transcript resume', async ({
  page,
  request,
}) => {
  await page.goto('/projects/supabase')
  await page.getByRole('button', { name: /Explicit/ }).click()
  const input = page.getByRole('textbox', { name: /message|question/i }).last()
  await input.fill(
    'Explain the difference between a missing SELECT grant and a row policy that matches no rows. Do not show SQL.',
  )
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  await expect(page.getByText(/Table privileges and row policies are separate checks/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'New session', exact: true })).toBeEnabled()
  await expect(page.getByText('Saved question awaiting an answer', { exact: true })).toHaveCount(0)
  const id = await page.evaluate(
    () =>
      Object.keys(localStorage)
        .filter((k) => k.startsWith('kaenguru.session.'))
        .map((k) => localStorage.getItem(k))[0],
  )
  const before = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(before.transcript).toHaveLength(2)
  await input.fill('Unsent notes for my next research step — keep these exactly.')
  await page.reload()
  await expect(input).toHaveValue('Unsent notes for my next research step — keep these exactly.')
  await expect(page.getByText('Saved question awaiting an answer', { exact: true })).toHaveCount(0)
  const after = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(after.transcript).toEqual(before.transcript)
})
