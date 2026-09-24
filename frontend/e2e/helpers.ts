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
