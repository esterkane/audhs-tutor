import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'
import axe from 'axe-core'

test.skip(process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Requires isolated project data and the indexed PostgreSQL manual')

for (const language of ['en', 'de']) {
  test(`source-extracted SQLSTATE lookup and full history resume (${language})`, async ({ page, request }) => {
    const status = await (await request.get(`${API_URL}/api/learning-focus/supabase`)).json()
    expect(status.study_provider).toBe('local')
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.response_language', value: language } })
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.persona', value: 'neutral' } })
    await page.setViewportSize({ width: language === 'de' ? 390 : 1280, height: 900 })
    await page.goto('/projects/supabase')
    const discussion = page.getByRole('button', { name: language === 'de' ? /Besprechen oder Fakten/ : /Discuss or look up facts/ })
    await expect(discussion).toBeVisible()
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () =>
      (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    await discussion.focus()
    await page.keyboard.press('Enter')
    const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    await expect(input).toBeVisible()
    const id = await page.evaluate(() => Object.keys(localStorage)
      .filter(key => key.startsWith('kaenguru.session.')).map(key => localStorage.getItem(key))[0])
    expect(id).toBeTruthy()
    const session = { id }
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
    const german = language === 'de'
    const summary = page.locator('summary').filter({ hasText: german ? 'NULL-Logik lokal vergleichen' : 'Compare NULL logic locally' })
    await summary.click()
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () =>
      (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    const outer = page.getByLabel(german ? 'Äußerer Wert (ganze Zahl oder null)' : 'Outer value (integer or null)')
    const inner = page.getByLabel(german ? 'Innere Werte (JSON-Liste)' : 'Inner values (JSON array)')
    const compare = page.getByRole('button', { name: german ? 'Lokal vergleichen' : 'Compare locally', exact: true })
    await input.fill('Unsent research note stays in the editor')
    for (const [index, example] of [
      { outer: '2', inner: '[1,null]', result: 'TRUE AND UNKNOWN = UNKNOWN' },
      { outer: '1', inner: '[1,null]', result: 'FALSE AND UNKNOWN = FALSE' },
      { outer: 'null', inner: '[]', result: german ? 'Die innere Menge ist leer' : 'The inner set is empty' },
    ].entries()) {
      await outer.fill(example.outer)
      await inner.fill(example.inner)
      await expect(compare).toBeEnabled()
      const calculation = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
      await compare.focus()
      await page.keyboard.press('Enter')
      const computed = await calculation
      expect(computed.ok()).toBe(true)
      await expect(page.getByText(example.result, { exact: false }).last()).toBeVisible()
      await expect(input).toHaveValue('Unsent research note stays in the editor')
      await expect(compare).toBeEnabled()
      const complete = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
      expect(complete.transcript).toHaveLength(4 + (index + 1) * 2)
      expect(complete.transcript.slice(0, 4)).toEqual(saved.transcript)
    }
    await inner.fill('[true]')
    await compare.click()
    await expect(page.getByRole('alert')).toContainText(german ? 'höchstens 20' : 'at most 20')
    const calculated = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
    expect(calculated.transcript).toHaveLength(10)
    await page.reload()
    await summary.click()
    await expect(inner).toHaveValue('[true]')
    await expect(input).toHaveValue('Unsent research note stays in the editor')
    const restored = await (await request.get(`${API_URL}/api/supabase-project/session/${session.id}`)).json()
    expect(restored.transcript).toEqual(calculated.transcript)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
