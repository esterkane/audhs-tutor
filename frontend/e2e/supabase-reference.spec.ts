import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Requires isolated project data and the indexed PostgreSQL manual')

for (const language of ['en', 'de']) {
  test(`source-extracted SQLSTATE lookup and full history resume (${language})`, async ({ page, request }) => {
    const status = await (await request.get(`${API_URL}/api/learning-focus/supabase`)).json()
    expect(status.study_provider).toBe('local')
    // Explicitly select the existing neutral discussion mode through the public session API.
    const created = await request.post(`${API_URL}/api/supabase-project/session`, {
      data: { mode: 'neutral', delivery: 'explicit', language, persona_on: false },
    })
    expect(created.ok()).toBe(true)
    const session = await created.json()
    await page.goto('/')
    await page.evaluate(({ user, id }) => localStorage.setItem(`kaenguru.session.${user}`, id),
      { user: status.user_id, id: session.id })
    await page.setViewportSize({ width: language === 'de' ? 390 : 1280, height: 900 })
    await page.goto('/projects/supabase')
    const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    await input.fill(language === 'de'
      ? 'Was bedeuten SQLSTATE 23514 und 23502?'
      : 'What do SQLSTATE 23514 and 23502 mean?')
    let response = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: language === 'de' ? 'Senden' : 'Send', exact: true }).click()
    expect((await response).ok()).toBe(true)
    await expect(page.getByRole('cell', { name: 'check_violation', exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'not_null_violation', exact: true })).toBeVisible()
    const first = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
    expect(first.transcript).toHaveLength(2)
    expect(first.mode).toBe('neutral')
    expect(first.transcript[1].tutor_turn.guard_flags).toEqual([])
    expect(first.transcript[1].tutor_turn.citations[0].url).toMatch(/postgresql.org\/docs\/\d+\/errcodes-appendix.html/)
    await page.reload()
    await expect(page.getByRole('cell', { name: 'check_violation', exact: true })).toBeVisible()
    await input.fill(language === 'de'
      ? 'Was bedeuten SQLSTATE 42501 und 40001?'
      : 'What do SQLSTATE 42501 and 40001 mean?')
    response = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: language === 'de' ? 'Senden' : 'Send', exact: true }).click()
    expect((await response).ok()).toBe(true)
    await expect(page.getByRole('cell', { name: 'insufficient_privilege', exact: true })).toBeVisible()
    await expect(page.getByRole('cell', { name: 'serialization_failure', exact: true })).toBeVisible()
    const saved = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
    expect(saved.transcript).toHaveLength(4)
    expect(saved.transcript.slice(0, 2)).toEqual(first.transcript)
    await page.reload()
    const resumed = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
    expect(resumed.transcript).toEqual(saved.transcript)
    await expect(page.getByRole('cell', { name: 'serialization_failure', exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
