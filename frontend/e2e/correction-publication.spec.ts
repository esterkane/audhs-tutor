import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

function fixture() {
  return execFileSync('uv', ['run', '--directory', 'backend', 'python', '-c', `
import asyncio, pathlib, os
from sqlalchemy import select
from app.db.session import make_engine, make_session_factory
from app.db import models
root=pathlib.Path.cwd().parent.resolve()
path=root/'data/sandbox.db'
assert path.is_file() and not path.is_symlink()
assert pathlib.Path(os.environ.get('SANDBOX_DB','./data/sandbox.db')) == pathlib.Path('data/sandbox.db')
async def main():
    engine=make_engine('sqlite+aiosqlite:///'+str(path))
    async with make_session_factory(engine)() as db:
        skill=await db.scalar(select(models.SkillNode.id).limit(1))
        doc=models.Document(title='Synthetic correction evidence', source_type='manual')
        db.add(doc); await db.flush()
        version=models.DocumentVersion(document_id=doc.id, content_hash='synthetic-v1')
        db.add(version); await db.flush()
        chunk=models.Chunk(document_version_id=version.id, ordinal=0, text='Two plus two equals four.')
        db.add(chunk); await db.flush()
        db.add(models.ChunkProvenance(chunk_id=chunk.id, source_id=doc.id, path='synthetic.txt', source_type='manual'))
        question=models.Assessment(skill_id=skill, kind='mcq', item_json={'question':'What is two plus two?', 'options':['Four','Five'], 'answer':0, 'explanation':'Two pairs make four.', 'source_chunk_id':chunk.id})
        db.add(question); await db.commit(); print(question.id)
    await engine.dispose()
asyncio.run(main())
`], { cwd: fileURLToPath(new URL('../../', import.meta.url)), encoding: 'utf8' }).trim()
}

for (const width of [390, 1280]) {
  test(`publish reviewed correction and recover lost response ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    const original = fixture()
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/corrections?assessment=${original}`)
    await page.getByRole('button', { name: 'Show reference answers and start a draft' }).click()
    await page.getByLabel('Question wording').fill('How many objects are in two pairs?')
    await page.getByRole('button', { name: 'Save correction draft' }).click()
    await expect(page.getByText('Draft version 2 saved. Practice is unchanged.')).toBeVisible()
    const id = new URL(page.url()).searchParams.get('draft')!
    await page.getByRole('button', { name: 'Load impact preview' }).click()
    const publish = page.getByRole('button', { name: 'Publish correction for my practice' })
    await expect(publish).toBeDisabled()
    await page.getByText(/Source .*available/).click()
    await expect(page.getByText('Two plus two equals four.')).toBeVisible()
    await page.getByRole('checkbox').focus(); await page.keyboard.press('Space')
    await expect(publish).toBeEnabled()
    await page.screenshot({ path: `/tmp/correction-publication-${width}.png`, fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    let writes = 0
    await page.route(`**/api/questions/correction-drafts/${id}/publish`, async route => {
      writes++
      const response = await route.fetch(); expect(response.status()).toBe(200)
      await route.abort('failed')
    })
    await publish.focus(); await page.keyboard.press('Enter')
    await expect(page.getByText(/The result is uncertain/)).toBeVisible()
    await page.reload()
    await page.getByRole('button', { name: 'Check save status' }).focus(); await page.keyboard.press('Enter')
    await expect(page.getByText('Correction published for your future practice. Previous answers and grades are retained.')).toBeVisible()
    await expect(page.getByLabel('Question wording')).toBeDisabled()
    expect(writes).toBe(1)
    const status = await request.get(`${API}/api/questions/${original}/practice`)
    await expectOk(status); expect((await status.json()).status.state).toBe('superseded')
    await page.reload()
    await expect(page.getByText('This correction was published. Its draft is retained for reference.')).toBeVisible()
    await endOpenSession(request)
  })
}
