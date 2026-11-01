import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'
import axe from 'axe-core'

test.skip(process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Requires isolated project data, the local disposable lab and indexed PostgreSQL references')

for (const language of ['en', 'de']) {
  test(`measured isolation, retry, draft retention and exact resume (${language})`, async ({ page, request }, info) => {
    const german = language === 'de'
    test.setTimeout(process.env.AUDHS_HOSTED_PROJECT_AUDIT === '1' ? 120000 : 45000)
    expect((await (await request.get(`${API_URL}/api/learning-focus/supabase`)).json()).study_provider).toBe('local')
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.response_language', value: language } })
    await request.put(`${API_URL}/api/preferences`, { data: { key: 'tutor.persona', value: 'neutral' } })
    await page.setViewportSize({ width: german ? 390 : 1280, height: 900 })
    await page.goto('/projects/supabase')
    await page.getByRole('button', { name: german ? /Besprechen oder Fakten/ : /Discuss or look up facts/ }).click()
    const input = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    await expect(input).toBeVisible()
    const id = await page.evaluate(() => Object.keys(localStorage)
      .filter(key => key.startsWith('kaenguru.session.')).map(key => localStorage.getItem(key))[0])
    expect(id).toBeTruthy()
    const title = german ? 'Transaktionsisolation lokal vergleichen' : 'Compare transaction isolation locally'
    const opener = page.getByRole('button', { name: title, exact: true })
    const dialog = page.getByRole('dialog', { name: title })
    await input.fill('Unsent research finding stays in my draft')
    await opener.focus()
    await page.keyboard.press('Enter')
    const workers = page.getByLabel(german ? 'Aktive Kräfte zu Beginn (2–20)' : 'Active workers at start (2–20)')
    const minimum = page.getByLabel(german ? 'Mindestanzahl aktiver Kräfte' : 'Minimum workers to keep active')
    const first = page.getByLabel(german ? 'Erster Commit-Versuch' : 'First commit attempt')
    const run = page.getByRole('button', { name: german ? 'Lokales Experiment ausführen' : 'Run local experiment', exact: true })
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () =>
      (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    let saved: { transcript: unknown[] } = { transcript: [] }
    for (const [index, example] of [
      { workers: '2', minimum: '1', first: 'a', marker: '1 > 1' },
      { workers: '3', minimum: '1', first: 'b', marker: '2 > 1' },
      { workers: '2', minimum: '2', first: 'a', marker: german ? 'Hier war kein Retry nötig' : 'No retry was needed' },
      { workers: '2', minimum: '0', first: 'b', marker: '1 > 0' },
    ].entries()) {
      if (index > 0) await opener.click()
      await expect(dialog).toBeVisible()
      await workers.fill(example.workers)
      await minimum.fill(example.minimum)
      await first.selectOption(example.first)
      const response = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
      const started = Date.now()
      await run.focus()
      await page.keyboard.press('Enter')
      expect((await response).ok()).toBe(true)
      await expect(page.getByText(example.marker, { exact: false }).last()).toBeVisible()
      await expect(opener).toBeEnabled()
      await expect(dialog).not.toBeVisible()
      const reading = await page.locator('section[aria-label="chat"] > div').first().boundingBox()
      expect(reading!.height).toBeGreaterThan(200)
      const complete = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
      expect(complete.transcript).toHaveLength((index + 1) * 2)
      expect(complete.transcript.slice(0, saved.transcript.length)).toEqual(saved.transcript)
      const turn = complete.transcript.at(-1).tutor_turn
      expect(turn.next_question).toBeNull()
      expect(turn.ledger_delta).toEqual([])
      expect(turn.text).toContain('read committed')
      expect(turn.text).toContain('repeatable read')
      expect(turn.text).toContain('serializable')
      expect(turn.citations.some((citation: { url: string }) => citation.url.match(
        /postgresql.org\/docs\/\d+\/(transaction-iso|mvcc-serialization-failure-handling).html/,
      ))).toBe(true)
      expect(turn.text).not.toContain('```json tutor_turn')
      await expect(input).toHaveValue('Unsent research finding stays in my draft')
      console.log(JSON.stringify({ language, case: index, end_to_end_ms: Date.now() - started }))
      saved = complete
    }
    await opener.click()
    await minimum.fill('3')
    await run.click()
    await expect(page.getByRole('alert')).toContainText(german ? 'Startanzahl' : 'starting count')
    const invalid = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(invalid.transcript).toEqual(saved.transcript)
    await page.reload()
    await opener.click()
    await expect(minimum).toHaveValue('3')
    await expect(first).toHaveValue('b')
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(opener).toBeFocused()
    await expect(input).toHaveValue('Unsent research finding stays in my draft')
    const restored = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(restored.transcript).toEqual(saved.transcript)
    const followup = german
      ? 'Vergleiche die Retry-Ergebnisse im ersten gespeicherten Versuch mit dem Minimum-null-Fall. Nutze gespeicherte Beobachtungen.'
      : 'Compare retry results in the first saved experiment with the minimum-zero case. Use stored observations.'
    await input.fill(followup)
    const reuseResponse = page.waitForResponse(r => r.url().endsWith('/supabase-project/turn'))
    const reuseStarted = Date.now()
    await input.press('Enter')
    expect((await reuseResponse).ok()).toBe(true)
    await expect(opener).toBeEnabled()
    const reused = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(reused.transcript).toHaveLength(saved.transcript.length + 2)
    expect(reused.transcript.slice(0, saved.transcript.length)).toEqual(saved.transcript)
    const evidenceAnswer = reused.transcript.at(-1).tutor_turn
    expect(evidenceAnswer.language).toBe(language)
    expect(evidenceAnswer.next_question).toBeNull()
    expect(evidenceAnswer.ledger_delta).toEqual([])
    expect(evidenceAnswer.text).toContain('1 > 1 = false')
    expect(evidenceAnswer.text).toContain('1 > 0 = true')
    expect(evidenceAnswer.text).toContain('2 > 1 = true')
    expect(evidenceAnswer.text).toContain('2 > 0 = true')
    expect(evidenceAnswer.text).toContain(german ? 'ursprüngliche Anzahl 2 übernommen' : 'reused original count 2')
    expect(evidenceAnswer.text).toContain('experiment1-')
    expect(evidenceAnswer.text).toContain('experiment4-')
    console.log(JSON.stringify({ language, saved_evidence_followup_ms: Date.now() - reuseStarted }))
    saved = reused
    await input.fill('Next research finding remains unsent')
    await page.reload()
    await expect(input).toHaveValue('Next research finding remains unsent')
    const evidenceResumed = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
    expect(evidenceResumed.transcript).toEqual(saved.transcript)
    if (process.env.AUDHS_HOSTED_PROJECT_AUDIT === '1') {
      try {
        await request.put(`${API_URL}/api/preferences`, {
          data: { key: 'authoring.daily_budget_cents', value: 100 },
        })
        await page.getByText('Tutor provider: local', { exact: true }).click()
        await page.getByRole('button', { name: 'Use OpenAI tutor', exact: true }).click()
        await expect(page.getByText('Tutor provider: openai', { exact: true })).toBeVisible()
        const text = german
          ? 'Vergleiche die Retry-Entscheidungen in unserem ersten lokalen Versuch (zwei aktive Kräfte, Minimum eins) mit dem späteren Minimum-null-Fall. Welche neue Anzahl las der vollständige Retry jeweils, welche Entscheidung folgte, und was übernahm der UPDATE-only-Versuch? Nutze die gespeicherten Beobachtungen. Keine SQL-Befehle, kein Quiz und keine Behauptung einer aktuellen Projektprüfung.'
          : 'Compare the retry decisions in our first local experiment (two active workers, minimum one) with our later minimum-zero case. What fresh count did the full retry see in each, what decision followed, and what did the UPDATE-only trial reuse? Use the stored observations. No SQL, quiz, or claims of inspecting a live project.'
        const started = Date.now()
        const response = await request.post(`${API_URL}/api/supabase-project/turn`, {
          data: { session_id: id, text, input_mode: 'text' }, timeout: 100000,
        })
        expect(response.ok()).toBe(true)
        const payload = await response.text()
        expect(payload).toContain('event: turn')
        expect(payload).not.toContain('event: error')
        expect(payload).not.toMatch(/"name"\s*:\s*"run_lab_sql"/)
        const followed = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
        expect(followed.transcript).toHaveLength(saved.transcript.length + 2)
        expect(followed.transcript.slice(0, saved.transcript.length)).toEqual(saved.transcript)
        const answer = followed.transcript.at(-1).tutor_turn
        expect(answer.language).toBe(language)
        expect(answer.next_question).toBeNull()
        expect(answer.text).toContain('1')
        expect(answer.text).toContain('0')
        expect(answer.text).toContain('experiment1-')
        expect(answer.text).toContain('experiment4-')
        console.log(JSON.stringify({ language, hosted_enabled_local_reuse_ms: Date.now() - started }))
        saved = followed
        await page.reload()
        const resumed = await (await request.get(`${API_URL}/api/supabase-project/session/${id}`)).json()
        expect(resumed.transcript).toEqual(saved.transcript)
        await expect(input).toHaveValue('Next research finding remains unsent')
      } finally {
        await request.put(`${API_URL}/api/learning-focus/supabase/study`, { data: { provider: 'local' } })
        await request.put(`${API_URL}/api/preferences`, { data: { key: 'authoring.daily_budget_cents', value: 0 } })
      }
    }

    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () =>
      (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.screenshot({ path: info.outputPath(`isolation-${language}.png`), fullPage: true })
  })
}
