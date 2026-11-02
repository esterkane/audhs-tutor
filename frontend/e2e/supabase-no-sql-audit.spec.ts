import { test, expect } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(
  process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Requires an isolated configured local project stack',
)

for (const language of ['en', 'de'])
  test(`reviewed explanation and incident respect no SQL and resume (${language})`, async ({
    page,
    request,
  }) => {
    const german = language === 'de'
    await request.put(`${API_URL}/api/preferences`, {
      data: { key: 'tutor.response_language', value: language },
    })
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.persona', value: 'neutral' } })
    await page.setViewportSize({ width: german ? 390 : 1280, height: 900 })
    await page.goto('/projects/supabase')
    await page.getByRole('button', { name: german ? /Erklärend/ : /Explicit/ }).click()
    const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    const question = german
      ? 'Erkläre den Unterschied zwischen fehlender SELECT-Berechtigung und RLS ohne passende Zeilen: keine Zeilen. Bitte keine SQL-Abfragen.'
      : 'Explain the difference between a missing SELECT grant and a row policy that matches no rows. Do not show SQL.'
    await input.fill(question)
    const answer = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: german ? 'Senden' : 'Send', exact: true }).click()
    expect((await answer).ok()).toBe(true)
    await expect(
      page.getByText(
        german ? /zwei getrennte Prüfungen/ : /Table privileges and row policies are separate checks/,
      ),
    ).toBeVisible()
    await expect(page.getByText(/has_table_privilege\(current_user/)).toHaveCount(0)
    await expect(page.locator('pre code')).toHaveCount(0)
    const id = await page.evaluate(
      () =>
        Object.keys(localStorage)
          .filter((k) => k.startsWith('kaenguru.session.'))
          .map((k) => localStorage.getItem(k))[0],
    )
    expect(id).toBeTruthy()
    const first = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(first.transcript).toHaveLength(2)
    await page.reload()
    await expect(
      page.getByText(
        german ? /zwei getrennte Prüfungen/ : /Table privileges and row policies are separate checks/,
      ),
    ).toBeVisible()
    // An incident starts through the real new-session control, not a hidden mode edit.
    await page.getByRole('button', { name: german ? 'Neue Sitzung' : 'New session', exact: true }).click()
    await page.getByRole('button', { name: german ? /Erklärend/ : /Explicit/ }).click()
    const incident = german
      ? 'Our SELECT fails: permission denied for table orders. Bitte keine SQL-Abfragen.'
      : 'Our SELECT fails: permission denied for table orders. Do not show SQL.'
    await input.fill(incident)
    const next = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: german ? 'Senden' : 'Send', exact: true }).click()
    expect((await next).ok()).toBe(true)
    await expect(
      page.getByText(german ? /Tabellenberechtigungsfehler/ : /The reported table permission error concerns/),
    ).toBeVisible()
    await expect(page.locator('pre code')).toHaveCount(0)
    const incidentId = await page.evaluate(
      () =>
        Object.keys(localStorage)
          .filter((k) => k.startsWith('kaenguru.session.'))
          .map((k) => localStorage.getItem(k))[0],
    )
    expect(incidentId).not.toBe(id)
    const saved = await (await request.get(`${API_URL}/api/supabase-project/session/${incidentId}`)).json()
    expect(saved.transcript).toHaveLength(2)
    expect(saved.mode).toBe('incident')
    const original = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(original.transcript).toEqual(first.transcript)
    await page.reload()
    await expect(
      page.getByText(german ? /Tabellenberechtigungsfehler/ : /The reported table permission error concerns/),
    ).toBeVisible()
    // An output restriction must not turn a reported deadlock into a negated report.
    await input.fill(
      german ? 'ERROR: deadlock detected. Ohne SQL.' : 'ERROR: deadlock detected. Do not show SQL.',
    )
    const deadlock = page.waitForResponse((r) => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: german ? 'Senden' : 'Send', exact: true }).click()
    expect((await deadlock).ok()).toBe(true)
    await expect(
      page.getByText(german ? /bezeichnet einen erkannten Deadlock/ : /identifies a detected deadlock/),
    ).toBeVisible()
    await expect(page.locator('pre code')).toHaveCount(0)
    const final = await (await request.get(`${API_URL}/api/supabase-project/session/${incidentId}`)).json()
    expect(final.transcript).toHaveLength(4)
    expect(final.transcript.slice(0, 2)).toEqual(saved.transcript)
    await page.reload()
    await expect(
      page.getByText(german ? /bezeichnet einen erkannten Deadlock/ : /identifies a detected deadlock/),
    ).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })

for (const language of ['en', 'de'])
  test(`neutral reviewed explanation has no quiz and resumes (${language})`, async ({ page, request }) => {
    const german = language === 'de'
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.response_language', value: language } })
    await page.goto('/projects/supabase')
    await page.getByRole('button', { name: german ? /Besprechen oder Fakten/ : /Discuss or look up facts/ }).click()
    const question = german
      ? 'Erkläre den Unterschied zwischen fehlender SELECT-Berechtigung und RLS ohne passende Zeilen: keine Zeilen. Bitte keine SQL-Abfragen.'
      : 'Explain the difference between a missing SELECT grant and a row policy that matches no rows. Do not show SQL.'
    await page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last().fill(question)
    const answer = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
    await page.getByRole('button', { name: german ? 'Senden' : 'Send', exact: true }).click()
    expect((await answer).ok()).toBe(true)
    const explanation = german ? /zwei getrennte Prüfungen/ : /Table privileges and row policies are separate checks/
    const quiz = german ? 'Welche Prüfung würdest du zuerst durchführen, und warum?' : 'Which check would you make first, and why?'
    await expect(page.getByText(explanation)).toBeVisible()
    await expect(page.getByText(quiz, { exact: true })).toHaveCount(0)
    await page.reload()
    await expect(page.getByText(explanation)).toBeVisible()
    await expect(page.getByText(quiz, { exact: true })).toHaveCount(0)
  })
