import { expect, test } from '@playwright/test'

// The Jupyter login redirect may carry a token in its URL.
test.use({ trace: 'off' })

test('open an uploaded working copy, run a cell explicitly and reopen the saved result', async ({ page, context }) => {
  test.skip(process.env.AUDHS_TEST_JUPYTER !== '1', 'Requires the installed local notebook environment')
  test.setTimeout(120_000)
  const notebook = {
    nbformat: 4, nbformat_minor: 5,
    metadata: { kernelspec: { name: 'python3', language: 'python', display_name: 'Python 3' } },
    cells: [{
      cell_type: 'code', id: 'practice', metadata: {}, execution_count: null, outputs: [],
      source: ['6 * 7'],
    }],
  }
  await page.goto('/curriculum?topic=supabase')
  await page.getByLabel('Material title', { exact: true }).fill('Notebook working copy')
  await page.getByLabel('Upload reference content (optional)').setInputFiles({
    name: 'practice.ipynb', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(notebook)),
  })
  await page.getByText('Open uploaded notebook locally', { exact: true }).click()
  await page.getByRole('button', { name: 'Prepare and start notebook lab' }).click()
  const link = page.getByRole('link', { name: 'Open prepared notebook in Jupyter' })
  await link.waitFor({ timeout: 30_000 })
  const href = await link.getAttribute('href')
  expect(href).toMatch(/^\/api\/notebooks\/open\/[\da-f-]{36}\/[\da-f-]{36}$/i)
  const opened = context.waitForEvent('page')
  await link.click()
  const lab = await opened
  const first = lab.locator('.jp-Notebook:visible .jp-CodeCell').first()
  await expect(first.locator('.cm-content')).toHaveText('6 * 7', { timeout: 30_000 })
  await expect(first.locator('.jp-OutputArea-output')).toHaveCount(0)
  await expect(lab.getByRole('button', { name: /Python 3.*Idle/ })).toBeVisible({ timeout: 30_000 })
  await first.locator('.cm-content').click()
  await lab.keyboard.press('End')
  await lab.keyboard.insertText('  # learner prediction')
  await lab.keyboard.press('Shift+Enter')
  await expect(first.locator('.jp-OutputArea-output')).toHaveText('42', { timeout: 30_000 })
  await lab.keyboard.press('Control+s')
  // Query Jupyter's saved document to ensure the result reached disk before closing.
  const documentUrl = new URL(lab.url())
  documentUrl.pathname = documentUrl.pathname.replace('/lab/tree/', '/api/contents/')
  await expect.poll(async () => {
    const response = await lab.request.get(documentUrl.toString())
    if (!response.ok()) return undefined
    const text = (await response.json()).content.cells[0].outputs[0]?.data?.['text/plain']
    return Array.isArray(text) ? text.join('') : text
  }).toEqual('42')
  await page.getByRole('button', { name: 'Check saved Jupyter edits' }).click()
  await page.getByRole('button', { name: 'Add cell to source notes' }).click()
  const notes = page.getByLabel('Your notes and selected source content')
  await expect(notes).toHaveValue(/6 \* 7 {2}# learner prediction/)
  await expect(notes).not.toHaveValue(/42/)
  await expect(page.getByRole('button', { name: 'Already in source notes' })).toBeDisabled()
  await page.getByRole('button', { name: 'Save knowledge material' }).click()
  await page.waitForURL(url => url.searchParams.has('draft'))
  await lab.close()
  await page.reload()
  await expect(notes).toHaveValue(/6 \* 7 {2}# learner prediction/)
  const disclosure = page.getByText('Open uploaded notebook locally', { exact: true })
  if (!(await link.isVisible())) await disclosure.click()
  if (!(await link.isVisible())) await page.getByRole('button', { name: 'Prepare and start notebook lab' }).click()
  const reopened = context.waitForEvent('page')
  await link.click()
  const second = await reopened
  await expect(second.locator('.jp-Notebook:visible .jp-CodeCell').first().locator('.jp-OutputArea-output')).toHaveText('42', { timeout: 30_000 })
  // Keep the rendered href and exercise it after its isolated Jupyter server exits.
  const opaque = new URL(href!, page.url()).href
  const outsider = await context.newPage()
  const otherOrigin = 'http://localhost:49991'
  await outsider.route(otherOrigin + '/fixture', route => route.fulfill({
    contentType: 'text/html', body: '<a href="' + opaque + '">Open earlier lab</a>',
  }))
  await outsider.goto(otherOrigin + '/fixture')
  const denied = outsider.waitForResponse(r => r.url() === opaque)
  await outsider.getByRole('link').click()
  const rejected = await denied
  expect(rejected.status()).toBe(403)
  expect(rejected.headers()['location']).toBeUndefined()
  await outsider.close()
  const stopped = await second.evaluate(async () => {
    const xsrf = document.cookie.split('; ').find(c => c.startsWith('_xsrf='))?.slice(6)
    const response = await fetch('/api/shutdown', {
      method: 'POST', headers: xsrf ? { 'X-XSRFToken': decodeURIComponent(xsrf) } : {},
    })
    return response.status
  })
  expect(stopped).toBe(200)
  await second.close()
  await expect.poll(async () => {
    const stale = await context.request.get(opaque, { maxRedirects: 0 })
    if (stale.status() === 409) {
      expect(stale.headers()['location']).toBeUndefined()
      expect(stale.headers()['cache-control']).toBe('no-store')
    }
    return stale.status()
  }, {timeout: 20_000}).toBe(409)
})
