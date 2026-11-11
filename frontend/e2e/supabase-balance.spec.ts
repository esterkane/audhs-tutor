import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'
test.skip(
  process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Requires an isolated configured project and disposable local SQL lab',
)
for (const language of ['en', 'de'])
  test(
    'observe relative and literal balance writes and restore the saved result ' + language,
    async ({ page, request }) => {
      const de = language === 'de'
      await request.put(API_URL + '/api/preferences', {
        data: { key: 'tutor.response_language', value: language },
      })
      await request.put(API_URL + '/api/preferences', { data: { key: 'tutor.persona', value: 'neutral' } })
      await page.setViewportSize({ width: de ? 390 : 1280, height: 900 })
      await page.goto('/projects/supabase')
      await page
        .getByRole('button', { name: de ? /Besprechen oder Fakten/ : /Discuss or look up facts/ })
        .click()
      const chat = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
      await chat.fill('Keep this unsent finding.')
      const toggle = page.getByRole('button', {
        name: de ? 'Zwei Updates auf demselben Konto' : 'Two updates on the same account',
        exact: true,
      })
      await toggle.press('Enter')
      const initial = page.getByLabel(de ? 'Kontostand zu Beginn' : 'Starting balance')
      const run = page.getByRole('button', {
        name: de ? 'Kontoversuch ausführen' : 'Run balance trial',
        exact: true,
      })
      await initial.fill('1000001')
      await run.click()
      await expect(
        page.getByRole('alert').filter({ hasText: de ? 'Gib ganze Zahlen' : 'Enter whole numbers' }),
      ).toBeVisible()
      await initial.fill('100')
      const id = await page.evaluate(
        () =>
          Object.keys(localStorage)
            .filter((k) => k.startsWith('kaenguru.session.'))
            .map((k) => localStorage.getItem(k))[0],
      )
      expect(id).toBeTruthy()
      const history = async () =>
        (await (await request.get(API_URL + '/api/supabase-project/session/' + id)).json()).transcript
      let previous = await history()
      for (const [mode, amount, result] of [
        ['subtract', '30', '50'],
        ['set', '70', '70'],
      ]) {
        await page.getByLabel(de ? 'Operation von B' : 'Operation for B').selectOption(mode)
        await page
          .getByLabel(
            de
              ? mode === 'set'
                ? 'Fester Kontostand für B'
                : 'Abbuchung durch B'
              : mode === 'set'
                ? 'Fixed balance for B'
                : 'Amount B subtracts',
          )
          .fill(amount)
        await run.press('Enter')
        const marker = (de ? 'Bestätigter Kontostand: ' : 'Committed balance: ') + result + '.'
        await expect(page.getByText(marker, { exact: false }).last()).toBeVisible({ timeout: 25000 })
        const contrast = de ? 'Der Kontostand bliebe 80.' : 'The balance would remain 80.'
        await expect(page.getByText(contrast, { exact: false }).last()).toBeVisible()
        const saved = await history()
        expect(saved.slice(0, previous.length)).toEqual(previous)
        expect(saved).toHaveLength(previous.length + 2)
        expect(saved.at(-1).tutor_turn.text).toContain(marker)
        expect(saved.at(-1).tutor_turn.text).toContain(contrast)
        previous = saved
        await page.reload()
        await expect(chat).toHaveValue('Keep this unsent finding.')
        await expect(page.getByText(marker, { exact: false }).last()).toBeVisible()
        await expect(page.getByText(contrast, { exact: false }).last()).toBeVisible()
        await toggle.press('Enter')
        await expect(page.getByLabel(de ? 'Operation von B' : 'Operation for B')).toHaveValue(mode)
        expect(await history()).toEqual(saved)
      }
    },
  )
