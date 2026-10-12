import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, freshDeterministicSkill } from './helpers'

for (const width of [390, 1280]) test(`repeated incorrect practice retains help and exit ${width}`, async ({ page, request }, info) => {
  await endOpenSession(request)
  try {
    const skill = freshDeterministicSkill()
    // Read only the newly cloned sandbox question to select a genuinely incorrect choice.
    const wrong = Number(execFileSync('python3', ['-c', `
import json,pathlib,sqlite3,sys
path=pathlib.Path('data/sandbox.db').resolve()
assert path == pathlib.Path.cwd()/'data/sandbox.db' and not pathlib.Path('data/sandbox.db').is_symlink()
db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
item=json.loads(db.execute('SELECT item_json FROM assessment WHERE skill_id=?',(sys.argv[1],)).fetchone()[0])
print((int(item['answer'])+1)%len(item['options']))
`, skill], { cwd: fileURLToPath(new URL('../../', import.meta.url)), encoding: 'utf8' }).trim())
    await page.setViewportSize({ width, height: 900 })
    for (const key of ['goal.area', 'goal.course']) await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value: '' } }))
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
    await expectOk(await request.post(`${API}/api/sessions/${session.id}/checkpoint`, { data: { phase: 'assess', skill_id: skill } }))
    let submissions = 0
    page.on('request', r => { if (r.method() === 'POST' && r.url().endsWith('/api/assess/attempt')) submissions++ })
    const help: { assessment_answer_id: string }[] = []
    await page.route('**/api/tutor/stream', route => {
      help.push(route.request().postDataJSON())
      const text = 'Synthetic help: compare the quantities in the worked example.'
      return route.fulfill({ contentType: 'text/event-stream', body: `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ text, turn_id: 'repeated-help', sources: [], dropped: [], flagged: [] })}\n\n` })
    })
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    let due = ''
    let rootAttempt = ''
    let latestAnswer = ''
    for (let attempt = 0; attempt < 3; attempt++) {
      if (attempt > 0) {
        await page.getByRole('button', { name: 'Try again', exact: true }).focus()
        await page.keyboard.press('Enter')
        await expect(page.getByRole('heading', { name: 'Try this question again' })).toBeVisible()
        await expect(page.getByRole('group', { name: 'Your answer', exact: true }).getByRole('button').first()).toBeFocused()
        await expect(page.getByRole('button', { name: 'Check my answer', exact: true })).toBeEnabled()
      }
      const choice = page.getByRole('group', { name: 'Your answer', exact: true }).getByRole('button').nth(wrong)
      await choice.focus()
      await page.keyboard.press('Enter')
      const checked = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/assess/attempt'))
      await page.getByRole('button', { name: 'Check my answer', exact: true }).focus()
      await page.keyboard.press('Enter')
      const gradeResponse = await checked
      expect(gradeResponse.ok()).toBe(true)
      const grade = await gradeResponse.json()
      expect(grade.score).toBe(0)
      latestAnswer = grade.answer_id
      expect(grade.confidence_pre).toBeNull()
      if (attempt > 0) {
        expect(grade.revision_of_attempt_id).toBe(rootAttempt)
        expect(grade.review_updated).toBe(false)
        expect(grade.review.due).toBe(due)
        await expect(page.getByText(/Repeated practice on a previously checked question/)).toBeVisible()
      } else { due = grade.review.due; rootAttempt = grade.attempt_id }
      await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled()
      if (attempt === 2) {
        await page.getByRole('button', { name: 'Explain the difficult part', exact: true }).focus()
        await page.keyboard.press('Enter')
        await expect(page.getByText('Synthetic help: compare the quantities in the worked example.', { exact: true })).toBeVisible()
        expect(help).toHaveLength(1)
        expect(help[0].assessment_answer_id).toBe(grade.answer_id)
      }
    }
    const before = await currentSession(request)
    await page.getByRole('button', { name: 'Pause and return Home', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.reload()
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await expect(page.getByRole('heading', { name: 'Feedback on your answer' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Try again', exact: true })).toBeEnabled()
    await expect(page.getByRole('button', { name: 'Next', exact: true })).toBeEnabled()
    await expect(page.getByRole('link', { name: 'Open saved feedback', exact: true })).toHaveAttribute('href', `/answers/${encodeURIComponent(latestAnswer)}`)
    expect(await currentSession(request)).toEqual(before)
    expect(submissions).toBe(3)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('heading', { name: 'Feedback on your answer' }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('repeated-incorrect.png') })
  } finally { await endOpenSession(request) }
})
