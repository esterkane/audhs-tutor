import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'

test('trace a selected scanned passage to its original PDF page after saving and reopening', async ({ page }) => {
  test.skip(process.env.AUDHS_TEST_PDF_OCR !== '1', 'Requires local Poppler and Tesseract')
  const root = resolve(import.meta.dirname, '../..')
  const pdf = execFileSync(resolve(root, 'backend/.venv/bin/python'), [
    '-c', [
      'import io, sys',
      'from pathlib import Path',
      'from pypdf import PdfReader, PdfWriter',
      'from tests.pdf_scan_fixture import native_pdf, scanned_pdf',
      'w = PdfWriter()',
      'w.append(PdfReader(io.BytesIO(native_pdf("Native permissions. Shared example."))))',
      'w.add_blank_page(width=612, height=792)',
      'w.append(PdfReader(io.BytesIO(scanned_pdf(Path(sys.argv[1]), text="Scanned visibility. Shared example."))))',
      'stream = io.BytesIO()', 'w.write(stream)', 'sys.stdout.buffer.write(stream.getvalue())',
    ].join('\n'), mkdtempSync(resolve(tmpdir(), 'mixed-page-fixture-')),
  ], { cwd: resolve(root, 'backend'), maxBuffer: 10 * 1024 * 1024 })
  await page.goto('/curriculum?topic=supabase')
  await page.getByLabel('Material title', { exact: true }).fill('Synthetic mixed PDF')
  const response = page.waitForResponse(r => r.url().endsWith('/knowledge-material/uploads'))
  await page.getByLabel('Upload reference content (optional)').setInputFiles({
    name: 'mixed-pages.pdf', mimeType: 'application/pdf', buffer: pdf,
  })
  const upload = await response
  expect(upload.ok(), await upload.text()).toBeTruthy()
  expect((await upload.json()).ocr_pages).toEqual([3])
  await page.getByText('Browse PDF pages', { exact: true }).filter({ visible: true }).click()
  await expect(page.getByRole('option', { name: 'Page 3 · OCR used' })).toBeAttached()
  await expect(page.getByRole('option', { name: 'Page 2', exact: true })).toHaveCount(0)
  const pdfPage = page.getByRole('combobox', { name: 'PDF page' })
  await pdfPage.selectOption({ label: 'Page 3 · OCR used' })
  const inspect = page.getByRole('button', {name:'Inspect original page 3'})
  await page.route('**/pages/3/preview', route => route.fulfill({ status: 429 }), { times: 1 })
  await inspect.press('Enter')
  await expect(page.getByRole('alert')).toContainText('could not be loaded')
  const retry = page.getByRole('button', { name: 'Retry original page 3' })
  await expect(retry).toBeFocused()
  const preview = page.waitForResponse(r => r.url().endsWith('/pages/3/preview'))
  await retry.press('Enter')
  const rendered = await preview
  expect(rendered.status()).toBe(200)
  expect(rendered.headers()['content-type']).toBe('image/png')
  const image = page.getByRole('img',{name:'Original uploaded PDF page 3'})
  await expect.poll(() => image.evaluate(e => (e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
  await page.getByRole('button',{name:'Enlarge page image'}).press('Enter')
  await expect(page.getByRole('region',{name:'Original PDF page image'})).toHaveAttribute('tabindex','0')
  const note = page.getByLabel('Your notes and selected source content')
  const correction = 'My verified reading of the scan is “Scanned visibility”.'
  await note.fill(await note.inputValue() + '\n\n' + correction)
  await page.getByRole('button', { name: '2. Research' }).click()
  await page.getByText('Browse PDF pages', { exact: true }).filter({ visible: true }).click()
  await page.getByRole('combobox', { name: 'PDF page' }).selectOption({ label: 'Page 3 · OCR used' })
  await expect(page.getByLabel('Extracted text from PDF page 3').filter({ visible: true })).toContainText('Scanned visibility.')
  const input = page.getByLabel('Exact source passage')
  await input.fill('Shared example.')
  await expect(page.getByText('Exact passage matches PDF pages 1, 3.')).toBeVisible()
  await input.fill('An independent learner note.')
  await expect(page.getByText('No exact page match in this PDF extraction.')).toBeVisible()
  await page.getByRole('button', { name: 'Use page 3 as passage' }).click()
  await page.getByLabel('Topic to investigate').fill('Row visibility')
  await page.getByRole('button', { name: 'Prepare research questions' }).click()
  await expect(page.getByText('Exact passage matches PDF page 3.')).toBeVisible()
  const saved = page.waitForResponse(r => r.url().endsWith('/knowledge-material/drafts') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  expect((await saved).ok()).toBeTruthy()
  await expect(page).toHaveURL(/draft=/)
  // Clear the tab's recovery cache so the saved server draft must supply its extraction identity.
  await page.evaluate(() => sessionStorage.clear())
  await page.reload()
  await expect(page.getByText('Exact passage matches PDF page 3.')).toBeVisible()
  await page.getByRole('button',{name:'1. Source'}).click()
  await expect(note).toHaveValue(new RegExp(correction))
  await page.getByText('Browse PDF pages', { exact: true }).filter({visible:true}).click()
  await pdfPage.selectOption({ label:'Page 3 · OCR used' })
  await inspect.press('Enter')
  await expect(image).toBeVisible()
  await expect(page.getByLabel('Extracted text from PDF page 3').filter({visible:true})).not.toContainText(correction)
  await page.getByRole('button', { name: '2. Research' }).click()
  await page.getByText('Read linked source passage').click()
  await expect(page.getByText('Scanned visibility. Shared example.', { exact: true }).filter({ visible: true })).toBeVisible()
})
