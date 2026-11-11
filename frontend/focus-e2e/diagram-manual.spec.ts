import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

for (const kind of ['diagram_pdf', 'vector_pdf'] as const) {
  test(`inspect ${kind}, add your own notes and reopen the saved draft`, async ({ page }) => {
    test.skip(process.env.AUDHS_TEST_PDF_OCR !== '1', 'Requires local Poppler and Tesseract')
    const root = resolve(import.meta.dirname, '../..')
    const pdf = execFileSync(resolve(root, 'backend/.venv/bin/python'), [
      '-c', `import sys; from tests.pdf_scan_fixture import ${kind}; sys.stdout.buffer.write(${kind}())`,
    ], { cwd: resolve(root, 'backend') })
    await page.goto('/curriculum?topic=supabase')
    const notes = page.getByLabel('Your notes and selected source content')
    const save = page.getByRole('button', { name: 'Save knowledge material', exact: true })
    await page.getByLabel('Upload reference content (optional)').setInputFiles({
      name: 'diagram.pdf', mimeType: 'application/pdf', buffer: pdf,
    })
    await expect(page.getByText(/No text was recognized. Open Browse PDF pages/)).toBeVisible()
    await expect(notes).toHaveValue('')
    await expect(save).toBeDisabled()
    const browse = page.getByText('Browse PDF pages', { exact: true }).filter({ visible: true })
    await browse.click()
    const inspect = page.getByRole('button', { name: 'Inspect original page 1' })
    await inspect.press('Enter')
    const image = page.getByRole('img', { name: 'Original uploaded PDF page 1' })
    await expect.poll(() => image.evaluate(e => (e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
    const description = 'My observation: the diagram shows an outlined rectangle.'
    await notes.fill(description)
    await save.click()
    await expect(page).toHaveURL(/draft=/)
    await page.evaluate(() => sessionStorage.clear())
    await page.reload()
    await expect(notes).toHaveValue(description)
    await browse.click()
    await inspect.press('Enter')
    await expect(image).toBeVisible()
  })
}
