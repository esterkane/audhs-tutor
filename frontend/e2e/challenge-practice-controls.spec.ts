import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) {
  test(`challenge exclusion preserves the answer ${width}`, async ({ page, request }) => {
    await endOpenSession(request)
    let assessmentId = ''
    try {
      const skillId = freshDeterministicSkill()
      assessmentId = execFileSync('python3', ['-c', `
import pathlib,sqlite3,json,sys
root=pathlib.Path.cwd().resolve(); path=root/'data/sandbox.db'
assert path.resolve()==path and not path.is_symlink()
db=sqlite3.connect(path.as_uri()+'?mode=rw',uri=True)
assert sys.argv[1].startswith('e2e-')
row=db.execute('select id from assessment where skill_id=?',(sys.argv[1],)).fetchone()
with db:
 db.execute('update assessment set kind=?,item_json=? where id=?',('challenge_planted_error',json.dumps({'prompt':'Synthetic challenge: find the error in this explanation.','criteria':['Identify the incorrect step'],'hidden_key':'Synthetic key','mode':'planted_error','sources':[]}),row[0]))
print(row[0])
`, skillId], { cwd: fileURLToPath(new URL('../../', import.meta.url)), encoding: 'utf8' }).trim()
      for (const key of ['goal.area', 'goal.course']) await request.put(`${API}/api/preferences`, { data: { key, value: '' } })
      const response = await request.post(`${API}/api/sessions`, { data: { mode: 'novelty', energy: 3 } })
      await expectOk(response)
      const session = await response.json()
      const index = session.plan.findIndex((b: { type: string }) => b.type === 'challenge')
      expect(index).toBeGreaterThanOrEqual(0)
      await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/')
      await page.getByRole('button', { name: 'Continue', exact: true }).click()
      await expect(page.getByRole('heading', { name: /^Challenge:/ })).toBeVisible()
      await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { skill_id: skillId } }))
      await page.reload()
      await page.getByRole('button', { name: /planted error/ }).click()
      await page.getByLabel('Your answer').fill('Keep my reasoning here.')
      await page.getByRole('button', { name: 'Question practice options' }).focus()
      await page.keyboard.press('Enter')
      await page.getByRole('button', { name: 'Exclude this question', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeDisabled()
      await expect(page.getByLabel('Your answer')).toHaveValue('Keep my reasoning here.')
      await page.getByLabel('Challenge practice choices').screenshot({ path: `/tmp/challenge-practice-${width}.png` })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
      await page.getByRole('button', { name: 'Restore this question', exact: true }).click()
      await page.getByRole('button', { name: 'Refresh restored challenge' }).focus()
      await page.keyboard.press('Enter')
      await expect(page.getByLabel('Challenge practice choices')).toBeFocused()
      await expect(page.getByRole('button', { name: 'Submit', exact: true })).toBeEnabled()
      await page.reload()
      await page.getByRole('button', { name: /planted error/ }).click()
      await expect(page.getByLabel('Your answer')).toHaveValue('Keep my reasoning here.')
    } finally {
      if (assessmentId) {
        const view = await (await request.get(`${API}/api/questions/${assessmentId}/practice`)).json()
        if (view.status.state === 'suspended') await expectOk(await request.post(`${API}/api/questions/${assessmentId}/practice`, { data: { request_id: crypto.randomUUID(), expected_revision: view.status.revision, action: 'restore' } }))
      }
      await endOpenSession(request)
    }
  })
}
