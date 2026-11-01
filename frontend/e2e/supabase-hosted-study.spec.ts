import { test, expect } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(
  process.env.AUDHS_HOSTED_PROJECT_AUDIT !== '1',
  'Requires isolated project data and explicitly enabled paid evaluation',
)

test('project provider setup failure, hosted answer and full transcript resume', async ({
  page,
  request,
}) => {
  test.setTimeout(120000)
  await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.persona', value: 'neutral' } })
  await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.response_language', value: 'en' } })
  await page.goto('/projects/supabase')
  await page.getByText('Tutor provider: local', { exact: true }).click()
  await page.getByRole('button', { name: 'Use OpenAI tutor', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('shared daily hosted budget')
  expect((await (await request.get(`${API_URL}/api/learning-focus/supabase`)).json()).study_provider).toBe(
    'local',
  )
  await request.put(`${API_URL}/api/preferences`, {
    data: { key: 'authoring.daily_budget_cents', value: 100 },
  })
  await page.getByRole('button', { name: 'Use OpenAI tutor', exact: true }).click()
  await expect(page.getByText('Tutor provider: openai', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: /Explicit/ }).click()
  const input = page.getByRole('textbox', { name: /message|question/i }).last()
  const question =
    'PostgreSQL: T1 SELECT reads x=10, then T2 commits x=11, then T1 SELECT reads again. Compare Read Committed and Repeatable Read for these ordinary SELECTs, with no locks or other writers. Explain both results directly. No SQL.'
  await input.fill(question)
  const response = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  expect((await response).ok()).toBe(true)
  await expect(page.getByRole('button', { name: 'New session', exact: true })).toBeEnabled({
    timeout: 100000,
  })
  const id = await page.evaluate(
    () =>
      Object.keys(localStorage)
        .filter((k) => k.startsWith('kaenguru.session.'))
        .map((k) => localStorage.getItem(k))[0],
  )
  expect(id).toBeTruthy()
  const saved = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(saved.transcript).toHaveLength(2)
  const answer = saved.transcript[1].content
  expect(JSON.stringify(answer)).toContain('11')
  expect(JSON.stringify(answer)).toContain('10')
  await page.reload()
  await expect(page.getByText('Tutor provider: openai', { exact: true })).toBeVisible()
  const resumed = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(resumed.transcript).toEqual(saved.transcript)
  await page.getByText('Tutor provider: openai', { exact: true }).click()
  await page.getByRole('button', { name: 'Use local tutor', exact: true }).click()
  await expect(page.getByText('Tutor provider: local', { exact: true })).toBeVisible()
  await request.put(`${API_URL}/api/preferences`, { data: { key: 'authoring.daily_budget_cents', value: 0 } })
  await page.getByRole('button', { name: 'Use OpenAI tutor', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('shared daily hosted budget')
  await page.reload()
  const afterFailure = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(afterFailure.transcript).toEqual(saved.transcript)
  expect((await (await request.get(`${API_URL}/api/learning-focus/supabase`)).json()).study_provider).toBe(
    'local',
  )
})
