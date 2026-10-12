import { expect, test } from '@playwright/test'

test('stalled CSV preview releases controls and cannot replace a later preview', async ({ page }) => {
  await page.addInitScript(() => {
    const original = window.fetch
    let calls = 0
    function response(word: string) {
      return new Response(JSON.stringify({ lang: 'de', rows: [{ row: 1, word, translation: 'house', example: null, status: 'new', problem: null }], columns: { word: 0, translation: 1 }, delimiter: ';', header: false, counts: { new: 1 }, errors: [] }), { headers: { 'Content-Type': 'application/json' } })
    }
    window.fetch = (...args) => {
      if (!String(args[0]).endsWith('/api/vocab/import/preview')) return original(...args)
      calls++
      if (calls > 1) return Promise.resolve(response('New preview'))
      // Intentionally ignores AbortSignal: an old transport response must remain harmless.
      return new Promise<Response>(resolve => {
        Object.assign(window, { releaseOldPreview: () => resolve(response('Old preview')) })
      })
    }
  })
  await page.goto('/vocab')
  const section = page.locator('details').filter({ has: page.locator('summary').filter({ hasText: /^Import a CSV list$/ }) })
  await section.locator('summary').first().click()
  await section.locator('summary').filter({ hasText: /^Or paste the list$/ }).click()
  await section.getByLabel('CSV text').fill('Haus;house')
  await page.clock.install()
  await section.getByRole('button', { name: 'Preview', exact: true }).click()
  await expect(section.getByRole('status')).toHaveText('Preparing preview…')
  await page.clock.fastForward(15001)
  await expect(section.getByRole('alert')).toContainText('took too long')
  await expect(section.getByLabel('CSV text')).toHaveValue('Haus;house')
  const retry = section.getByRole('button', { name: 'Preview', exact: true })
  await expect(retry).toBeEnabled()
  await retry.focus()
  await page.keyboard.press('Enter')
  await expect(section.getByLabel('Word, row 1')).toHaveValue('New preview')
  await page.evaluate(() => (window as unknown as { releaseOldPreview: () => void }).releaseOldPreview())
  await expect(section.getByLabel('Word, row 1')).toHaveValue('New preview')
})
