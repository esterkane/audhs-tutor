import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { API, expectOk, freshDeterministicSkill } from './helpers'

// Real review HTTP/database writes, restricted to a fresh disposable sandbox task.
for (const width of [390, 1280]) test(`Task review persists without learning claims ${width}`, async ({ page, request }) => {
  const skill = freshDeterministicSkill()
  const assessment = execFileSync('python3', ['-c', `
import json,pathlib,sqlite3,sys,uuid
path=pathlib.Path('data/sandbox.db')
assert not path.is_symlink() and path.resolve() == pathlib.Path.cwd()/'data/sandbox.db'
db=sqlite3.connect(path.resolve().as_uri()+'?mode=rw',uri=True)
db.row_factory=sqlite3.Row
db.execute('PRAGMA foreign_keys=ON')
a=dict(db.execute('SELECT * FROM assessment WHERE skill_id=?',(sys.argv[1],)).fetchone())
r=dict(db.execute('SELECT * FROM assessment_rubric LIMIT 1').fetchone())
r.update(id=str(uuid.uuid4()),criteria_json=json.dumps([{'criterion':'Explain why missingness changes representation'}]))
with db:
    db.execute('INSERT INTO assessment_rubric ('+','.join(r)+') VALUES ('+','.join('?' for _ in r)+')',list(r.values()))
    db.execute('UPDATE assessment SET kind=?,rubric_id=?,item_json=? WHERE id=?',('explain_back',r['id'],json.dumps({'prompt':'Why can removing incomplete rows exclude some groups?'}),a['id']))
print(a['id'])
`, skill], { cwd: fileURLToPath(new URL('../../', import.meta.url)), encoding: 'utf8' }).trim()
  const path = `${API}/api/questions/${assessment}/task-review`
  const evidence = () => request.get(`${API}/api/skills/${skill}/evidence`)
  const before = await evidence(); await expectOk(before)
  const baseline = await before.json()
  await page.setViewportSize({ width, height: 900 })
  await page.goto(`/task-review?assessment=${assessment}`)
  await page.getByRole('button', { name: 'Show task and rubric' }).click()
  await expect(page.getByText('Why can removing incomplete rows exclude some groups?', { exact: true })).toBeVisible()
  await page.getByRole('checkbox').focus(); await page.keyboard.press('Space')
  await page.getByRole('button', { name: 'Approve this task review' }).focus(); await page.keyboard.press('Enter')
  await expect(page.getByText('Task review saved. This does not change your grades or confirm understanding.')).toBeFocused()
  await page.reload()
  await page.getByRole('button', { name: 'Show task and rubric' }).click()
  await expect(page.getByText(/Approval matches this content/)).toBeVisible()
  await expect(page.getByRole('checkbox')).not.toBeChecked()
  const saved = await request.get(path); await expectOk(saved)
  expect((await saved.json()).current_review).toMatchObject({ revision: 1, decision: 'approve' })
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: 'Revoke previous approval' }).focus(); await page.keyboard.press('Enter')
  await expect(page.getByText('Review revoked. Your review history and past answers are kept.')).toBeFocused()
  await page.reload()
  await page.getByRole('button', { name: 'Show task and rubric' }).click()
  await expect(page.getByText(/Latest review: revoked/)).toBeVisible()
  const revoked = await request.get(path); await expectOk(revoked)
  expect((await revoked.json()).current_review).toMatchObject({ revision: 2, decision: 'revoke' })
  const after = await evidence(); await expectOk(after)
  expect(await after.json()).toEqual(baseline)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
})
