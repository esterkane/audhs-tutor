import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`saved follow-up sends explicitly and retains lineage (${width}px)`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      let held = false
      window.fetch = async (input, init) => {
        const response = await original(input, init)
        if (held || !String(input).endsWith('/followup/stream')) return response
        held = true
        const finalEvents = await response.text()
        const encoder = new TextEncoder()
        return new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(
                encoder.encode(
                  'event: token\ndata: {"text":"Compare each group before drawing a conclusion."}\n\n',
                ),
              )
              ;(window as Window & { releaseFollowup?: () => void }).releaseFollowup = () => {
                controller.enqueue(encoder.encode(finalEvents))
                controller.close()
              }
            },
          }),
          { headers: { 'Content-Type': 'text/event-stream' } },
        )
      }
    })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'session' } }))
    let feedback = { verdict: null as string | null, note: '', hidden: false, revision: 0 }
    await page.route('**/api/answers/*/feedback', async (route) => {
      if (route.request().method() === 'PUT')
        feedback = { ...route.request().postDataJSON(), revision: feedback.revision + 1 }
      await route.fulfill({ json: feedback })
    })
    const parent = {
      id: 'parent',
      text: 'Compare group representation.',
      request_text: 'Why compare?',
      request: {},
      metadata: {},
      created_at: '2026-10-01T10:00:00Z',
    }
    await page.route('**/api/answers/parent', (route) => route.fulfill({ json: parent }))
    let historyReads = 0
    await page.route('**/api/answers?*', async (route) => {
      const params = new URL(route.request().url()).searchParams
      expect(params.get('parent_answer_id')).toBe('parent')
      historyReads++
      await route.fulfill({
        json: {
          items: [{ ...parent, id: 'child', learner_question: 'Show a small example.' }],
          next_cursor: null,
        },
      })
    })
    let preferred: string | null = null
    let revision = 0
    await page.route('**/api/answers/parent/replacement', async (route) => {
      if (route.request().method() === 'PUT') {
        const body = route.request().postDataJSON()
        expect(body.revision).toBe(revision)
        preferred = body.replacement_id
        revision++
      }
      await route.fulfill({ json: { replacement_id: preferred, revision } })
    })
    let calls = 0
    await page.route('**/api/answers/parent/followup/stream', async (route) => {
      calls++
      expect(route.request().postDataJSON()).toEqual({
        session_id: 'session',
        question: 'Show a small example.',
        purpose: 'correction',
      })
      await route.fulfill({
        contentType: 'text/event-stream',
        body: `event: done\ndata: ${JSON.stringify({ turn_id: 'turn', text: 'Illustrative: compare 9/10 with 6/10.', answer_id: 'child' })}\n\n`,
      })
    })
    await page.route('**/api/answers/child', (route) =>
      route.fulfill({
        json: {
          ...parent,
          id: 'child',
          text: 'Illustrative: compare 9/10 with 6/10.',
          request_text: 'Show a small example.',
          request: { historical_answer: { answer: parent.text, truncated_fields: [] } },
          metadata: { parent_answer_id: 'parent', followup_purpose: 'correction' },
        },
      }),
    )
    await page.goto('/answers/parent')
    await page.getByRole('combobox', { name: 'How was this answer?' }).selectOption('incorrect')
    await page.getByRole('textbox', { name: 'Why? (optional)' }).fill('Check the totals')
    await page.getByRole('button', { name: 'Save feedback', exact: true }).click()
    await expect(page.getByText('Feedback saved.')).toBeVisible()
    await expect(page.getByText(/The reply you will continue from is marked incorrect/)).toBeVisible()
    const input = page.getByRole('textbox', { name: 'Your follow-up question' })
    await expect(input).toBeVisible()
    expect(calls).toBe(0)
    await page.getByRole('button', { name: 'Prepare correction request' }).click()
    await expect(page.getByRole('combobox', { name: 'Request type' })).toHaveValue('correction')
    expect(calls).toBe(0)
    await input.fill('Show a small example.')
    const send = page.getByRole('button', { name: 'Send follow-up' })
    await send.focus()
    await page.keyboard.press('Enter')
    const preview = page.getByRole('region', { name: 'Unfinished follow-up' })
    await expect(preview).toContainText('Compare each group before drawing a conclusion.')
    await expect(page.getByRole('link', { name: 'Open saved follow-up' })).not.toBeVisible()
    await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible()
    await preview.scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('followup-streaming.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.evaluate(() => (window as Window & { releaseFollowup?: () => void }).releaseFollowup?.())
    await expect(preview).not.toBeVisible()

    await expect(page.getByText('Illustrative: compare 9/10 with 6/10.')).toBeVisible()
    expect(calls).toBe(1)
    await page.getByRole('link', { name: 'Open saved follow-up' }).click()
    await expect(page.getByRole('link', { name: 'previous saved answer' })).toHaveAttribute(
      'href',
      '/answers/parent',
    )
    await expect(page.getByText(/This is a proposed correction, not a verified replacement/)).toBeVisible()
    await page.getByText('Review this correction as your preferred reply', { exact: true }).click()
    const prefer = page.getByRole('button', { name: 'Prefer this correction', exact: true })
    await expect(prefer).toBeDisabled()
    await page
      .getByRole('checkbox', { name: 'I reviewed both answers and want to prefer this correction.' })
      .check()
    await prefer.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Preferred correction saved. Both answers remain in history.')).toBeVisible()
    expect(preferred).toBe('child')
    await page.getByRole('button', { name: 'Undo preferred correction' }).click()
    await expect(page.getByText('Preference removed. Existing feedback still applies.')).toBeVisible()
    expect(preferred).toBeNull()
    await page.getByText('Historical context supplied for this reply').click()
    await expect(page.getByText(/Compare group representation/)).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByRole('link', { name: 'previous saved answer' }).click()
    await expect(page.getByRole('link', { name: 'latest saved follow-up' })).toHaveAttribute(
      'href',
      '/answers/child',
    )
    expect(historyReads).toBe(0)
    await page.getByText('Later replies to this answer', { exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('link', { name: 'Show a small example.', exact: true })).toHaveAttribute(
      'href',
      '/answers/child',
    )
    expect(historyReads).toBe(1)
    expect(calls).toBe(1)
  })
}

test('unsaved follow-up can be recovered after refresh without a new request identity', async ({ page }, info) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'session' } }))
  await page.route('**/api/answers/parent', route => route.fulfill({ json: { id: 'parent', text: 'Original explanation', request_text: 'Explain', request: {}, metadata: {}, created_at: '2026-10-01T10:00:00Z' } }))
  await page.route('**/api/answers/*/feedback', route => route.fulfill({ json: { verdict: null, note: '', hidden: false, revision: 0 } }))
  await page.route('**/api/answers?*', route => route.fulfill({ json: { items: [], total: 0 } }))
  const keys: (string | undefined)[] = []
  await page.route('**/api/answers/parent/followup/stream', route => {
    keys.push(route.request().headers()['idempotency-key'])
    return route.fulfill({ contentType: 'text/event-stream', body: `event: done\ndata: ${JSON.stringify({ turn_id: 'unsaved', text: 'Keep this completed explanation.', save_error: 'Save unavailable', save_receipt: 'receipt' })}\n\n` })
  })
  await page.goto('/answers/parent')
  await page.getByRole('textbox', { name: 'Your follow-up question' }).fill('Why?')
  await page.getByRole('button', { name: 'Send follow-up', exact: true }).click()
  await expect(page.getByText('Keep this completed explanation.', { exact: true })).toBeVisible()
  await page.reload()
  const retry = page.getByRole('button', { name: 'Retry previous request', exact: true })
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Keep this completed explanation.', { exact: true })).toBeVisible()
  expect(keys).toHaveLength(2)
  expect(keys[0]).toBeTruthy()
  expect(keys[1]).toBe(keys[0])
  await expect(page.getByRole('button', { name: 'Send follow-up', exact: true })).toBeDisabled()
  await page.screenshot({ path: info.outputPath('unsaved-recovered.png'), fullPage: true })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
