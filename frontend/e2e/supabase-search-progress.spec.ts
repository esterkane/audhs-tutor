import axe from 'axe-core'
import { test, expect } from '@playwright/test'
import { API_URL } from '../playwright.config'

test.skip(
  process.env.AUDHS_SUPABASE_CONFIGURED_AUDIT !== '1',
  'Needs the isolated configured Supabase project',
)
for (const language of ['en', 'de'])
  test('documentation progress and completed answer ' + language, async ({ page, request }) => {
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
    // Control only event delivery; session creation, the composer and SSE parser use the ordinary project path.
    await page.evaluate(() => {
      const original = window.fetch
      window.fetch = (input, init) => {
        if (!String(input).endsWith('/supabase-project/turn')) return original(input, init)
        return Promise.resolve(
          new Response(
            new ReadableStream<Uint8Array>({
              start(controller) {
                Object.assign(window, {
                  emitTutorEvent: (kind: string, data: unknown) => {
                    controller.enqueue(
                      new TextEncoder().encode('event: ' + kind + '\ndata: ' + JSON.stringify(data) + '\n\n'),
                    )
                    if (kind === 'turn') controller.close()
                  },
                })
              },
            }),
            { headers: { 'Content-Type': 'text/event-stream' } },
          ),
        )
      }
    })
    const emit = (event: string, data: unknown) =>
      page.evaluate(
        ([e, d]) => {
          ;(window as unknown as { emitTutorEvent: (e: string, d: unknown) => void }).emitTutorEvent(
            e as string,
            d,
          )
        },
        [event, data],
      )
    const compose = page.getByRole('textbox', { name: /message|question|nachricht|frage/i }).last()
    await compose.fill(de ? 'Welche Dokumentation erklärt das?' : 'Which documentation explains this?')
    await compose.press('Enter')
    const chat = page.locator('section[aria-label="chat"]')
    const status = chat
      .getByRole('status')
      .filter({ hasText: de ? /Warten|durchsucht/ : /Waiting|Searching/ })
    await expect(status).toBeVisible()
    await emit('tool_call', { name: 'search_docs', input: { query: 'unavailable lookup' } })
    await emit('tool_result_summary', { name: 'search_docs', is_error: true, summary: 'unavailable' })
    await expect(status).toContainText(
      de ? 'Dokumentationssuche fehlgeschlagen' : 'Documentation search failed',
    )
    for (const query of ['first passage', 'second passage'])
      await emit('tool_call', { name: 'search_docs', input: { query } })
    await expect(status).toHaveText(de ? 'Dokumentation wird durchsucht…' : 'Searching documentation…')
    await emit('tool_result_summary', { name: 'search_docs', is_error: false, summary: 'one result' })
    await expect(status).toHaveText(de ? 'Dokumentation wird durchsucht…' : 'Searching documentation…')
    await emit('tool_result_summary', { name: 'search_docs', is_error: false, summary: 'one result' })
    await expect(status).toContainText(
      de ? 'Dokumentationssuche abgeschlossen' : 'Documentation search finished',
    )
    await expect(chat.getByText('search_docs', { exact: false })).toHaveCount(0)
    await page.addScriptTag({ content: axe.source })
    expect(
      await page.evaluate(
        async () =>
          (await (window as unknown as { axe: typeof axe }).axe.run('section[aria-label="chat"]')).violations,
      ),
    ).toEqual([])
    await emit('token', { text: 'An unverified candidate sentence.' })
    await expect(chat.getByText('An unverified candidate sentence.')).toHaveCount(0)
    await expect(status).toContainText(
      de ? 'Dokumentationssuche abgeschlossen' : 'Documentation search finished',
    )
    await emit('turn', {
      turn_id: 'test',
      model: 'fixture',
      usage: {},
      turn: {
        mode: 'teach',
        language,
        persona_on: false,
        text: 'Completed answer.',
        speech: '',
        citations: [],
        diagrams: [],
        ledger_delta: [],
        guard_flags: [],
      },
    })
    await expect(chat.getByText('Completed answer.')).toBeVisible()
    await expect(status).toHaveCount(0)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  })
