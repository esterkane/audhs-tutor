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
  const streamed = await response
  expect(streamed.ok()).toBe(true)
  const payload = await streamed.text()
  expect(payload).toContain('event: tool_call')
  const toolResults = payload
    .replace(/\r/g, '')
    .split('\n\n')
    .filter((block) => block.startsWith('event: tool_result_summary'))
    .map((block) =>
      JSON.parse(
        block
          .split('\n')
          .find((line) => line.startsWith('data:'))!
          .slice(5),
      ),
    )
  expect(toolResults.some((result) => result.name === 'search_docs' && result.is_error === false)).toBe(true)
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
  let saved = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(saved.transcript).toHaveLength(2)
  const turn = saved.transcript[1].tutor_turn
  expect(turn.mode).toBe("lesson")
  // Explicit delivery permits a useful check; it does not require one per answer.
  if (turn.next_question) {
    expect(turn.text).toContain("?")
    expect(turn.next_question.match(/\?/g)?.length).toBe(1)
  }
  expect(turn.guard_flags ?? []).not.toContain("NO_QUESTION")
  expect(
    turn.citations.some((citation: { url: string }) =>
      citation.url.startsWith('https://www.postgresql.org/docs/'),
    ),
  ).toBe(true)
  expect(turn.guard_flags ?? []).not.toContain('CITATION_NOT_FROM_TOOL')
  expect(turn.guard_flags ?? []).not.toContain('UNCITED_CLAIM')
  const answer = saved.transcript[1].content
  expect(JSON.stringify(answer)).toContain('11')
  expect(JSON.stringify(answer)).toContain('10')
  await input.fill(
    'In pgvector, compare <->, <=> and <#>: identify each measure, explain ascending ordering and the negative sign, and whether inner-product and cosine rankings are guaranteed to agree without normalized embeddings. Answer completely with indexed sources. No SQL or quiz.',
  )
  await page.getByRole('button', { name: 'Send', exact: true }).click()
  await expect(page.getByRole('button', { name: 'New session', exact: true })).toBeEnabled({ timeout: 100000 })
  const continued = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
  expect(continued.transcript).toHaveLength(4)
  expect(continued.transcript.slice(0, 2)).toEqual(saved.transcript)
  const vectorTurn = continued.transcript[3].tutor_turn
  expect(vectorTurn.mode).toBe("lesson")
  expect(vectorTurn.next_question).toBeNull()
  expect(vectorTurn.text.trim()).not.toMatch(/^\{\s*"(?:text|state|tools)"/)
  expect(vectorTurn.text).not.toContain('"next_question":')
  expect(vectorTurn.guard_flags ?? []).not.toContain('NO_QUESTION')
  expect(vectorTurn.text).toContain('<->')
  expect(vectorTurn.text).toContain('<=>')
  expect(vectorTurn.text).toContain('<#>')
  expect(vectorTurn.text).toMatch(/negative|negated|negation/i)
  expect(vectorTurn.citations.some((c: { url: string }) =>
    c.url.startsWith('https://supabase.com/docs/guides/ai/vector-columns.md') ||
    /^https:\/\/github\.com\/pgvector\/pgvector\/blob\/(?:master|v\d+\.\d+\.\d+)\/README\.md(?:#|$)/.test(c.url),
  )).toBe(true)
  expect(vectorTurn.guard_flags ?? []).not.toContain('CITATION_NOT_FROM_TOOL')
  expect(vectorTurn.guard_flags ?? []).not.toContain('UNCITED_CLAIM')
  saved = continued
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
