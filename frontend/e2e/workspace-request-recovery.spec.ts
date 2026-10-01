import { expect, test } from '@playwright/test'

for (const width of [1280, 390]) {
  for (const surface of ['study', 'playground']) {
    test(`recovers lost ${surface} reply after reload (${width}px)`, async ({ page }, testInfo) => {
      await page.setViewportSize({ width, height: 850 })
      await page.route('**/api/sessions/current', (route) =>
        route.fulfill({ json: { id: 'fixture-session' } }),
      )
      await page.route('**/local-learning/program.json', (route) =>
        route.fulfill({
          json: {
            title: 'Practice',
            courses: [
              {
                id: 'fixture',
                title: 'Data',
                project: 'Inspect',
                status: 'Fixture',
                sections: [
                  {
                    id: 'section',
                    title: 'Missingness',
                    explanation: 'Cleaning changes representation.',
                    example: 'Group A retains 90 rows; group B retains 60.',
                    task: 'Compare groups',
                    question: 'Why might equal rules have unequal effects?',
                    hint: 'Compare retention.',
                    criteria: 'Explain representation changes.',
                    source: 'Fixture',
                  },
                ],
              },
            ],
          },
        }),
      )
      let generations = 0
      let originalKey = ''
      let originalBody = ''
      await page.route('**/api/playground/tutor', async (route) => {
        const key = route.request().headers()['idempotency-key']
        expect(key).toMatch(/^[a-f0-9-]{36}$/)
        if (!originalKey) {
          originalKey = key
          originalBody = route.request().postData() ?? ''
          generations++
          // The simulated server completes, but its HTTP response is lost.
          await route.abort('failed')
        } else {
          expect(key).toBe(originalKey)
          expect(route.request().postData()).toBe(originalBody)
          await route.fulfill({
            json: {
              text: 'Recovered: compare which groups remain.',
              turn_id: 'one-turn',
              model: 'fixture',
              route: 'fake',
              source_note: 'Synthetic guidance',
            },
          })
        }
      })
      await page.goto(surface === 'study' ? '/programs' : '/playground')
      if (surface === 'study') {
        await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
        await page.getByLabel('Your explanation').fill('Different proportions remain')
        await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
      } else {
        await page.getByRole('button', { name: 'One hint', exact: true }).click()
      }
      await expect(page.getByRole('button', { name: 'Retry previous request', exact: true })).toBeVisible()
      await page.reload()
      if (surface === 'study') await page.getByRole('button', { name: 'Think deeper', exact: true }).click()
      const retry = page.getByRole('button', { name: 'Retry previous request', exact: true })
      await expect(retry).toBeVisible()
      await page.screenshot({ path: testInfo.outputPath('retry-controls.png'), fullPage: true })
      await retry.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('Recovered: compare which groups remain.')).toBeVisible()
      await expect(retry).toHaveCount(0)
      expect(generations).toBe(1)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
      await page.screenshot({ path: testInfo.outputPath('recovered.png'), fullPage: true })
    })
  }
}

test('explicitly continues tutoring when tab storage is denied', async ({ page }) => {
  await page.addInitScript(() => Object.defineProperty(window, 'sessionStorage', {
    configurable: true,
    get() { throw new DOMException('Denied', 'SecurityError') },
  }))
  await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'fixture-session' } }))
  let calls = 0
  await page.route('**/api/playground/tutor', async route => {
    calls++
    expect(route.request().headers()['idempotency-key']).toMatch(/^[a-f0-9-]{36}$/)
    await route.fulfill({ json: { text: 'Keep a copy of your code.', turn_id: 'turn', model: 'fixture', route: 'fake', source_note: 'Fixture' } })
  })
  await page.goto('/playground')
  await page.getByRole('button', { name: 'Continue without reload recovery', exact: true }).click()
  await page.getByRole('button', { name: 'One hint', exact: true }).click()
  await expect(page.getByText('Keep a copy of your code.')).toBeVisible()
  await expect(page.getByText(/Retry is kept only while this page stays open/)).toBeVisible()
  expect(calls).toBe(1)
})
