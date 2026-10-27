import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  test(`notebook focus and Socratic follow-up at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.addInitScript(() => {
      const original = window.fetch.bind(window)
      let held = false
      window.fetch = async (input, init) => {
        const response = await original(input, init)
        if (held || !String(input).endsWith('/api/playground/tutor/stream')) return response
        held = true
        const finalEvents = await response.text()
        const encoder = new TextEncoder()
        return new Response(
          new ReadableStream({
            start(controller) {
              controller.enqueue(
                encoder.encode(
                  'event: token\ndata: {"text":"A preview arrives before the completed explanation."}\n\n',
                ),
              )
              ;(window as Window & { releaseStudyReply?: () => void }).releaseStudyReply = () => {
                controller.enqueue(encoder.encode(finalEvents))
                controller.close()
              }
            },
          }),
          { headers: { 'Content-Type': 'text/event-stream' } },
        )
      }
    })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'fixture-session' } }))
    await page.route('**/local-learning/program.json', (route) =>
      route.fulfill({
        json: {
          title: 'Practice',
          courses: [
            {
              id: 'fixture',
              title: 'Example',
              project: 'Study',
              status: 'Fixture',
              sections: [],
              notebook: '/local-learning/example.ipynb',
            },
          ],
        },
      }),
    )
    await page.route('**/local-learning/example.ipynb', (route) =>
      route.fulfill({
        json: {
          nbformat: 4,
          nbformat_minor: 5,
          metadata: {},
          cells: [
            { cell_type: 'markdown', source: '# Inspect\nLook at missing data.', metadata: {} },
            { cell_type: 'code', source: 'count = 2', metadata: {}, outputs: [], execution_count: null },
            { cell_type: 'markdown', source: '# Compare\nCompare group retention.', metadata: {} },
            {
              cell_type: 'code',
              source: 'retained = [90, 60]',
              metadata: {},
              outputs: [],
              execution_count: null,
            },
          ],
        },
      }),
    )
    let requests = 0
    let release: (() => void) | undefined
    await page.route('**/api/playground/tutor{,/stream}', async (route) => {
      const body = route.request().postDataJSON()
      expect(body.questioning_style).toBe(requests < 2 ? 'socratic' : 'explicit')
      expect(body.exercise).toContain('Compare group retention')
      expect(body.learning_context.course_id).toBe('fixture')
      expect(body.learning_context.target_label).toBe('Step — Compare')
      expect(body.learning_context.target_id).toContain(':2:step')
      if (requests === 1) {
        expect(body.question).toContain('My answer to your last question')
        expect(body.history).toHaveLength(2)
        expect(body.learner_question).toBe('The groups have different sizes.')
        expect(body.learner_answer).toBe('The groups have different sizes.')
      }
      const text =
        requests++ === 0
          ? 'Why compare proportions rather than counts?'
          : 'You identified unequal group sizes. What would you compare next?'
      if (requests === 6)
        await new Promise<void>((resolve) => {
          release = resolve
        })
      const final = {
        text,
        model: 'fixture',
        route: 'fake',
        turn_id: 'fixture',
        source_note: 'Synthetic historical context',
        memory_answers: ['prior'],
        reused: body.prefer_saved,
        saved_at: '2026-10-01T09:00:00Z',
      }
      await route.fulfill({
        contentType: 'text/event-stream',
        body: `event: done\ndata: ${JSON.stringify(final)}\n\n`,
      })
    })
    await page.route('**/api/answers?*', async (route) => {
      const query = new URL(route.request().url()).searchParams
      expect(query.get('course_id')).toBe('fixture')
      if (query.has('target_id')) expect(query.get('target_id')).toContain(':2:step')
      await route.fulfill({
        json: {
          items: [
            {
              id: 'prior',
              learner_question: 'Why compare rates?',
              preview: 'Group sizes differ.',
              created_at: '2026-10-01T10:00:00Z',
            },
          ],
          next_cursor: null,
        },
      })
    })
    await page.goto('/programs')
    if (width === 390)
      await page.addStyleTag({
        content: 'body { font-family: Arial, sans-serif; } input[type=file] { font-size: 20px; }',
      })
    await page.getByText('Saved answers for this course').click()
    await expect(page.getByRole('link', { name: 'Browse all answers for this course' })).toHaveAttribute(
      'href',
      '/answers?surface=playground&course_id=fixture',
    )
    await page.getByText('Saved answers for this course').click()
    await page.getByText('Full course notebook and files', { exact: true }).click()
    await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
    await page.getByText('Read or edit a notebook in this page', { exact: true }).click()
    await page.getByRole('button', { name: 'Open saved project notebook' }).click()
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('2')
    await expect(page.getByRole('combobox', { name: 'Notebook cell', exact: true })).toHaveValue('0')
    await expect(page.getByText('Discussing: Step — Compare')).toBeVisible()
    await page.getByText('Previously answered here').click()
    const savedLink = page.getByRole('link', { name: 'Why compare rates?' })
    await expect(savedLink).toBeVisible()
    await expect(savedLink).toHaveAttribute('href', /course_id=fixture/)
    await page.getByText('Previously answered here').click()
    await page.getByText('Saved-answer reuse options · off', { exact: true }).click()
    const reuse = page.getByRole('checkbox', { name: /Use a saved answer/ })
    await reuse.focus()
    await page.keyboard.press('Space')
    await expect(reuse).toBeChecked()
    await page.getByText('Practice with a guided question (optional)', { exact: true }).click()
    const socratic = page.getByRole('button', { name: 'Ask me a Socratic question', exact: true })
    await socratic.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('region', { name: 'Unfinished tutor reply' })).toContainText(
      'A preview arrives',
    )
    await expect(
      page.getByText('Why compare proportions rather than counts?', { exact: true }),
    ).not.toBeVisible()
    await page.screenshot({ path: info.outputPath('streaming-preview.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.evaluate(() => (window as Window & { releaseStudyReply?: () => void }).releaseStudyReply?.())
    await expect(page.getByRole('region', { name: 'Unfinished tutor reply' })).not.toBeVisible()
    const answer = page.getByLabel('Your answer to the tutor’s question', { exact: true })
    await expect(answer).toBeFocused()
    await expect(page.getByText(/Saved answer from 2026-10-01/)).toBeVisible()
    await answer.fill('The groups have different sizes.')
    await page.getByRole('button', { name: 'Discuss my answer', exact: true }).click()
    await expect(
      page.getByText('You identified unequal group sizes. What would you compare next?'),
    ).toBeVisible()
    await page.getByText('Earlier messages (2)', { exact: true }).click()
    await expect(page.getByText('Why compare proportions rather than counts?', { exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Open previous answer', exact: true })).toHaveAttribute(
      'href',
      '/answers/prior',
    )
    await answer.fill('Keep this draft')
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('0')
    await expect(page.getByText('Discussing: Step — Inspect')).toBeVisible()
    await page.getByRole('combobox', { name: 'Tutor focus', exact: true }).selectOption('2')
    await expect(answer).toHaveValue('Keep this draft')
    expect(requests).toBe(2)
    await page.getByText('Saved-answer reuse options · on', { exact: true }).click()
    await expect(page.getByRole('checkbox', { name: /Use a saved answer/ })).toBeChecked()
    await page.getByRole('button', { name: 'Explain instead', exact: true }).click()
    const draft = page.getByLabel('Your tutor message or response', { exact: true })
    await expect(draft).toHaveValue('Keep this draft')
    for (const label of ['Shorter', 'Smaller steps', 'Show an example']) {
      const control = page.getByRole('button', { name: label, exact: true })
      await control.focus()
      await page.keyboard.press('Enter')
      if (label === 'Show an example') {
        await expect(page.getByRole('status', { name: 'Tutor response status' })).toContainText('preparing')
        await expect(page.getByText(/Waiting [1-9]\d* seconds?/)).toBeVisible()
        const stop = page.getByRole('button', { name: 'Stop tutor response', exact: true })
        await stop.focus()
        await page.keyboard.press('Enter')
        await expect(page.getByRole('status', { name: 'Tutor response status' })).toBeEmpty()
        release!()
        await control.click()
      }
      await expect(control).toBeEnabled()
      await expect(draft).toHaveValue('Keep this draft')
      await expect(page.getByText('Discussing: Step — Compare')).toBeVisible()
    }
    expect(requests).toBe(7)
    await expect(page.getByRole('status', { name: 'Tutor response status' })).toHaveText(
      'Tutor response ready.',
    )
    const overflow = await page.evaluate(() =>
      [...document.querySelectorAll('body *')]
        .filter((el) => {
          const rect = el.getBoundingClientRect()
          return rect.width > 0 && rect.right > innerWidth + 1
        })
        .map((el) => ({
          tag: el.tagName,
          text: el.textContent?.slice(0, 90),
          className: el.className,
          right: el.getBoundingClientRect().right,
        })),
    )
    expect(overflow).toEqual([])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
