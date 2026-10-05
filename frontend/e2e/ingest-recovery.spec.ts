import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`reconciled import needs explicit keyboard resume at ${width}`, async ({ page }, info) => {
    const root = fileURLToPath(new URL('../../', import.meta.url))
    const fixture = JSON.parse(execFileSync('uv', ['run', '--directory', 'backend', 'python', '-c', `
import asyncio, json, os, pathlib, subprocess, sys, tempfile
from app.db.session import make_engine, make_session_factory
from app.knowledge.ingest.recovery import reconcile_abandoned_runs
root = pathlib.Path(sys.argv[1]).resolve()
database = root / 'data' / 'sandbox.db'
assert database.is_file() and database.resolve() == database and not database.is_symlink()
assert pathlib.Path(os.environ.get('SANDBOX_DB', './data/sandbox.db')) == pathlib.Path('data/sandbox.db')
source = pathlib.Path(tempfile.mkdtemp(prefix='ingest-recovery-', dir=root / 'data'))
(source / 'one.md').write_text('# First\\n\\nA synthetic source about data cleaning.')
(source / 'two.md').write_text('# Second\\n\\nA different synthetic source about missing values.')
child = '''
import asyncio, os, sys
from pathlib import Path
from app.db.session import make_engine, make_session_factory
from app.knowledge.ingest.service import IngestOptions, ingest_path
def progress(p):
    if p.done == 1:
        print(p.run_id, flush=True)
        os._exit(77)
async def main():
    engine = make_engine('sqlite+aiosqlite:///' + sys.argv[1])
    async with make_session_factory(engine)() as db:
        await ingest_path(db, Path(sys.argv[2]), options=IngestOptions(media=False, progress=progress))
asyncio.run(main())
'''
result = subprocess.run([sys.executable, '-c', child, str(database), str(source)], capture_output=True, text=True, timeout=20)
assert result.returncode == 77, result.stderr
async def reconcile():
    engine = make_engine('sqlite+aiosqlite:///' + str(database))
    try:
        assert await reconcile_abandoned_runs(make_session_factory(engine)) == 1
    finally:
        await engine.dispose()
asyncio.run(reconcile())
print(json.dumps({'run': result.stdout.strip(), 'source': str(source)}))
`, root], { cwd: root, encoding: 'utf8' })) as { run: string; source: string }
    try {
      let starts = 0
      page.on('request', request => {
        if (request.url().endsWith('/api/corpus/ingest/jobs') && request.method() === 'POST') starts++
      })
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/corpus?ingestJob=missing-before-restart')
      await expect(page.getByText('Add course material and ingestion progress', { exact: true })).toBeVisible()
      await expect(page.getByText('Could not retrieve ingestion progress:', { exact: false })).toBeVisible()
      await page.getByText(/^Interrupted runs you can resume/).click()
      const row = page.locator('li').filter({ hasText: fixture.source.split('/').at(-1) })
      await expect(row).toContainText('1 of 2 files done')
      expect(starts).toBe(0)
      const resume = row.getByRole('button', { name: 'Resume', exact: true })
      await resume.focus()
      await page.keyboard.press('Enter')
      await expect(page.getByText('already done before the resume', { exact: false })).toBeVisible()
      expect(starts).toBe(1)
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.getByText('already done before the resume', { exact: false }).scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath('resumed-import.png') })
    } finally {
      execFileSync('python3', ['-c', `
import pathlib, shutil, sys
root = pathlib.Path(sys.argv[1]).resolve()
source = pathlib.Path(sys.argv[2])
assert source.parent == root / 'data' and source.name.startswith('ingest-recovery-') and not source.is_symlink()
shutil.rmtree(source)
`, root, fixture.source])
    }
  })
}
