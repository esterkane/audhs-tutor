import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, type APIRequestContext, type Page } from '@playwright/test'
import { API_URL } from '../playwright.config'

/** The sandbox backend started by `make sandbox-backend` (see playwright.config.ts). */
export const API = API_URL

/** `expect(res.ok())` loses the body; keep it in the failure message. */
export async function expectOk(res: { status(): number; text(): Promise<string> }) {
  expect(res.status(), await res.text()).toBeLessThan(300)
}

export type SessionState = {
  block_index: number | null
  block_status: string | null
  phase: string | null
  block?: { type: string } | null
}

export async function currentSession(request: APIRequestContext) {
  const res = await request.get(`${API}/api/sessions/current`)
  await expectOk(res)
  return (await res.json()) as null | { id: string; state?: SessionState | null }
}

/** Every test starts and ends with no open session, so Home offers "Start session". */
export async function endOpenSession(request: APIRequestContext) {
  const s = await currentSession(request)
  if (s?.id) {
    const res = await request.post(`${API}/api/sessions/${s.id}/end`, {
      data: { energy_after: 3, self_report: 3 },
    })
    await expectOk(res)
  }
}

export async function startFromHome(page: Page) {
  await page.goto('/')
  await page.getByRole('button', { name: 'Start session' }).click()
}

export async function expectServerBlock(
  request: APIRequestContext,
  expected: { type: string; phase: string },
) {
  const s = await currentSession(request)
  expect(s?.state?.block_status).toBe('running')
  expect(s?.state?.block?.type).toBe(expected.type)
  expect(s?.state?.phase).toBe(expected.phase)
}

export async function skillIdBySlug(request: APIRequestContext, slug: string) {
  const { skills } = (await (await request.get(`${API}/api/skills`)).json()) as {
    skills: Array<{ id: string; slug: string }>
  }
  const hit = skills.find((s) => s.slug === slug)
  expect(hit, `seeded skill ${slug}`).toBeTruthy()
  return hit!.id
}

/** Start → movement → skip → review done → continue: the learn block on the first skill. */
export async function reachLearnBlock(page: Page) {
  await startFromHome(page)
  await page.getByRole('button', { name: /then new material/ }).click()
  await expect(page.getByRole('heading', { name: 'Movement block' })).toBeVisible()
  await page.getByRole('button', { name: 'Skip this block' }).click()
  await finishReview(page)
  await page.getByRole('button', { name: 'Continue the plan' }).click()
  await expect(page.getByRole('heading', { name: /^Learn: / })).toBeVisible()
}

/**
 * Rate every due card (confidence 3, then Good) until the review block reports done. Journeys
 * share one sandbox database, so a card scheduled by an earlier journey may still be due here.
 */
export async function finishReview(page: Page) {
  const done = page.getByRole('heading', { name: 'Review done' })
  for (let i = 0; i < 20; i++) {
    if (await done.isVisible()) return
    const show = page.getByRole('button', { name: 'Show answer' })
    if (await show.isVisible()) {
      await show.click()
      await page.getByRole('button', { name: /^Good/ }).click()
    } else {
      await page.waitForTimeout(200)
    }
  }
  await expect(done).toBeVisible()
}

/** Isolated deterministic content in this checkout's disposable sandbox only.
 * Never clear attempts: recovery journeys must exercise real persisted learning writes.
 * Untaught fixture skills cannot change another journey's automatic next-skill selection.
 */
export function freshDeterministicSkill(): string {
  const root = fileURLToPath(new URL('../../', import.meta.url))
  return execFileSync('python3', ['-c', `
import json, pathlib, sqlite3, uuid
root = pathlib.Path.cwd().resolve()
expected = root / 'data' / 'sandbox.db'
assert expected.is_file() and not expected.is_symlink(), 'Seeded sandbox DB required'
assert expected.resolve() == expected, 'Sandbox path must not redirect outside checkout'
import os
assert pathlib.Path(os.environ.get('SANDBOX_DB', './data/sandbox.db')) == pathlib.Path('data/sandbox.db'), 'Custom sandbox DB unsupported by fixture'
db = sqlite3.connect(expected.as_uri() + '?mode=rw', uri=True)
db.row_factory = sqlite3.Row
db.execute('PRAGMA foreign_keys=ON')
skill = dict(db.execute("SELECT * FROM skill_node WHERE slug='dot-product'").fetchone() or {})
if not skill:
    skill = dict(db.execute("SELECT s.* FROM skill_node s JOIN assessment a ON a.skill_id=s.id WHERE a.kind='mcq' ORDER BY s.created_at,s.id LIMIT 1").fetchone())
original = skill['id']
skill_id = 'e2e-' + str(uuid.uuid4())
def insert(table, row):
    columns = ','.join('"'+k+'"' for k in row)
    db.execute('INSERT INTO '+table+' ('+columns+') VALUES ('+','.join('?' for _ in row)+')', list(row.values()))
skill.update(id=skill_id, slug=skill_id, title='Isolated deterministic practice', course=None, area_id=None, assessment_requirements_json=json.dumps({'teachable':False}))
with db:
    insert('skill_node', skill)
    learning = dict(db.execute('SELECT * FROM learning_object WHERE skill_id=? ORDER BY version DESC LIMIT 1',(original,)).fetchone())
    learning.update(id='e2e-'+str(uuid.uuid4()), skill_id=skill_id)
    insert('learning_object', learning)
    assessment = dict(db.execute("SELECT * FROM assessment WHERE skill_id=? AND kind='mcq' ORDER BY id LIMIT 1",(original,)).fetchone())
    assessment.update(id='e2e-'+str(uuid.uuid4()), skill_id=skill_id)
    insert('assessment', assessment)
print(skill_id)
`], { cwd: root, encoding: 'utf8' }).trim()
}

export async function openMainMenu(page: import('@playwright/test').Page) {
  const menu = page.getByRole('button', { name: /^Menu ·/ })
  if (await menu.isVisible()) await menu.click()
}
