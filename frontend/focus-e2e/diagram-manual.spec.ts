import { expect, test } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { API, endOpenSession, expectOk } from '../e2e/helpers'
import { resolve } from 'node:path'

for (const kind of ['diagram_pdf', 'vector_pdf'] as const) {
  test(`inspect ${kind} and reopen its original page in a saved lesson`, async ({ page, request }) => {
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
    const title = `Reading an uploaded ${kind}`
    await page.getByLabel('Material title', { exact: true }).fill(title)
    await notes.fill(description)
    await save.click()
    await expect(page).toHaveURL(/draft=/)
    await page.evaluate(() => sessionStorage.clear())
    await page.reload()
    await expect(notes).toHaveValue(description)
    await browse.click()
    await inspect.press('Enter')
    await expect(image).toBeVisible()
    const original = await image.getAttribute('src')
    await page.getByRole('button', { name: 'Write a lesson from my notes' }).click()
    await page.getByLabel('Learning objective', { exact: true }).fill('Describe a rectangle.')
    await page.getByLabel('Explanation', { exact: true }).fill(description)
    await page.getByLabel('Worked example', { exact: true }).fill('The outline contains four corners.')
    await page.getByLabel('Application question', { exact: true }).fill('What is the shape?')
    await page.getByLabel(/Success criteria/).fill('Names the rectangle.')
    await page.getByRole('button', { name: 'Next', exact: true }).click()
    await save.click()
    const accepting = page.waitForResponse(r => r.url().endsWith('/publish'))
    await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
    await expectOk(await accepting)
    const skills = (await (await request.get(API + '/api/skills')).json()).skills
    const skill = skills.find((s: {title: string}) => s.title === title)
    await endOpenSession(request)
    await page.goto('/?lesson=' + skill.id)
    const started = page.waitForResponse(r => r.url().endsWith('/api/sessions') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
    const session = await (await started).json()
    await expectOk(await request.post(API + '/api/plan/blocks/start', { data: {
      session_id: session.id, index: session.plan.findIndex((b: {type:string}) => b.type === 'new_material'),
    }}))
    await page.goto('/session')
    await page.reload()
    await page.getByText('Your notes and source references', {exact:true}).click()
    await page.getByRole('button', {name:'Original PDF source'}).press('Enter')
    await browse.click()
    await inspect.press('Enter')
    await expect(image).toHaveAttribute('src', original!)
    await expect.poll(() => image.evaluate(e => (e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)
    await endOpenSession(request)
  })
}
