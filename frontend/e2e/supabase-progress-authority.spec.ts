import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(process.env.AUDHS_SUPABASE_PROGRESS_FAULT_AUDIT !== '1',
  'Requires an isolated learner and a deliberately faulty SDK client; never run against real learner data')

for (const language of ['en', 'de']) {
  test(`neutral discussion blocks invented mastery and recovers the complete question (${language})`, async ({ page, request }) => {
    test.setTimeout(45000)
    const german = language === 'de'
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.response_language', value: language } })
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.persona', value: 'neutral' } })
    await page.goto('/projects/supabase')
    await page.getByRole('button', { name: german ? /Besprechen oder Fakten/ : /Discuss or look up facts/ }).click()
    const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    await expect(input).toBeVisible()
    const id = await page.evaluate(() => Object.keys(localStorage).filter(key => key.startsWith('kaenguru.session.')).map(key => localStorage.getItem(key))[0])
    const submit = async (question: string) => {
      await input.fill(question)
      const response = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
      await input.press('Enter')
      expect((await response).ok()).toBe(true)
      await expect(page.getByRole('button', { name: german ? 'Neue Sitzung' : 'New session', exact: true })).toBeEnabled()
    }
    await submit('Explain the difference between a missing SELECT grant and a row policy that matches no rows. Do not show SQL.')
    const before = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(before.transcript).toHaveLength(2)
    const ledger = await (await request.get(`${API_URL}/api/supabase-project/ledger`)).json()
    const question = `[progress-authority:${language}:fault] Discuss my research findings without assessing me. Keep this full question — 🦘.`
    await submit(question)
    await expect(page.getByRole('alert')).toBeVisible()
    const rejected = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(rejected.transcript).toEqual(before.transcript)
    expect(await (await request.get(`${API_URL}/api/supabase-project/ledger`)).json()).toEqual(ledger)
    await page.reload()
    await expect(page.getByText(german ? 'Gespeicherte Frage wartet auf eine Antwort' : 'Saved question awaiting an answer', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: german ? 'Frage im Editor wiederherstellen' : 'Restore question to editor', exact: true }).click()
    await expect(input).toHaveValue(question)
    await submit(question)
    await expect(page.getByRole('alert')).toHaveCount(0)
    const completed = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(completed.transcript).toHaveLength(4)
    expect(completed.transcript.slice(0, 2)).toEqual(before.transcript)
    expect(completed.transcript.at(-1).tutor_turn.language).toBe(language)
    expect(completed.transcript.at(-1).tutor_turn.ledger_delta).toEqual([])
    expect(await (await request.get(`${API_URL}/api/supabase-project/ledger`)).json()).toEqual(ledger)
    await input.fill('My next unsent finding remains exact — 🦘')
    await page.reload()
    await expect(input).toHaveValue('My next unsent finding remains exact — 🦘')
    expect((await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()).transcript).toEqual(completed.transcript)
  })
}
