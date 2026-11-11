import { expect, test } from '@playwright/test'

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
  const opened = context.waitForEvent('page')
  await link.click()
  const lab = await opened
  const first = lab.locator('.jp-Notebook .jp-CodeCell').first()
  await expect(first.locator('.cm-content')).toHaveText('6 * 7', { timeout: 30_000 })
  await expect(first.locator('.jp-OutputArea-output')).toHaveCount(0)
  await first.locator('.cm-content').click()
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
  await lab.close()
  await page.reload()
  const disclosure = page.getByText('Open uploaded notebook locally', { exact: true })
  if (!(await link.isVisible())) await disclosure.click()
  if (!(await link.isVisible())) await page.getByRole('button', { name: 'Prepare and start notebook lab' }).click()
  const reopened = context.waitForEvent('page')
  await link.click()
  const second = await reopened
  await expect(second.locator('.jp-Notebook .jp-CodeCell').first().locator('.jp-OutputArea-output')).toHaveText('42', { timeout: 30_000 })
  await second.close()
})
