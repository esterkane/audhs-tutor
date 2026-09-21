import { expect, test, type APIRequestContext } from '@playwright/test'
import {
  API,
  currentSession,
  endOpenSession,
  expectOk,
  expectServerBlock,
  finishReview,
  startFromHome,
} from './helpers'

/**
 * Browser journeys over the real stack (ADR-0013): Vite → FastAPI → the sandbox SQLite seeded by
 * `make dev-sandbox`. They prove what the component tests cannot — that a reload, a second tab or a
 * resume from Home lands on the block the *server* owns (P1 `session-transitions`), that the review
 * screen collects confidence before revealing (P1 `review-confidence`) and that "Stop here" keeps the
 * plan resumable. Nothing here talks to a hosted model: the sandbox runs with an empty API key and a
 * zero budget, and every journey below stays on deterministic screens.
 */

/**
 * Make one review card due *now* using only public routes: answer an assessment of the skill at
 * `skillIndex` (an item is created on the first attempt), then re-rate it with the API's
 * dev/benchmark `as_of` time travel three days in the past so its next due date lies behind us.
 * Each journey uses its own skill: `next_item` rotates mcq → cloze → explain_back per skill, and
 * the third kind is graded by a local model the CI runner does not have — the assertion below
 * fails loudly instead of waiting on a model timeout.
 */
async function makeOneCardDue(request: APIRequestContext, skillIndex: number) {
  const started = await request.post(`${API}/api/sessions`, {
    data: { mode: 'steady', energy: 3, socratic: false },
  })
  await expectOk(started)
  const session = (await started.json()) as { id: string }
  const { skills } = (await (await request.get(`${API}/api/skills`)).json()) as {
    skills: Array<{ id: string }>
  }
  const next = await request.get(
    `${API}/api/assess/next?session_id=${session.id}&skill_id=${skills[skillIndex].id}`,
  )
  await expectOk(next)
  const { item } = (await next.json()) as { item: { id: string; kind: string } | null }
  expect(item).not.toBeNull()
  expect(['mcq', 'cloze'], 'deterministically graded kinds only (no local model in CI)').toContain(item!.kind)
  const attempt = await request.post(`${API}/api/assess/attempt`, {
    data: { session_id: session.id, assessment_id: item!.id, answer: 'no idea', confidence_pre: 1 },
  })
  await expectOk(attempt)
  const far = new Date(Date.now() + 30 * 86_400_000).toISOString()
  const due = (await (
    await request.get(`${API}/api/review/due?session_id=${session.id}&as_of=${far}&all=true`)
  ).json()) as { items: Array<{ item_id: string; skill_id: string }> }
  const mine = due.items.find((d) => d.skill_id === skills[skillIndex].id)
  expect(mine, 'the attempt created a review card for this skill').toBeTruthy()
  const past = new Date(Date.now() - 3 * 86_400_000).toISOString()
  const rated = await request.post(`${API}/api/review/${mine!.item_id}?as_of=${past}`, {
    data: { session_id: session.id, rating: 1 },
  })
  await expectOk(rated)
  await endOpenSession(request)
}

test.beforeEach(async ({ request }) => endOpenSession(request))
test.afterEach(async ({ request }) => endOpenSession(request))

test('a reload at every block boundary lands on the block the server owns', async ({ page, request }) => {
  await startFromHome(page)
  await expect(page.getByRole('heading', { name: 'Which first?' })).toBeVisible()
  await page.getByRole('button', { name: /then new material/ }).click()

  await expect(page.getByRole('heading', { name: 'Movement block' })).toBeVisible()
  await expectServerBlock(request, { type: 'movement_primer', phase: 'practice' })
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Movement block' })).toBeVisible()

  await page.getByRole('button', { name: 'Skip this block' }).click()
  await finishReview(page) // cards left due by an earlier journey are rated away first
  await expect(page.getByRole('heading', { name: 'Review done' })).toBeVisible()
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Review done' })).toBeVisible()

  await page.getByRole('button', { name: 'Continue the plan' }).click()
  await expect(page.getByRole('heading', { name: /^Learn: / })).toBeVisible()
  await expectServerBlock(request, { type: 'new_material', phase: 'teach' })
  await page.reload()
  await expect(page.getByRole('heading', { name: /^Learn: / })).toBeVisible()

  // a second tab of the same session shows the same block — no client state decides it
  const other = await page.context().newPage()
  await other.goto('/session')
  await expect(other.getByRole('heading', { name: /^Learn: / })).toBeVisible()
  await other.close()
})

test('review asks for confidence before revealing, then the plan continues', async ({ page, request }) => {
  await makeOneCardDue(request, 0)
  await startFromHome(page)
  await page.getByRole('button', { name: /^Review \(/ }).click()

  const confidence = page.getByRole('group', { name: /how sure are you of your recall/i })
  await expect(confidence).toBeVisible()
  const show = page.getByRole('button', { name: 'Show answer' })
  await expect(show).toBeDisabled()
  await confidence.getByRole('button', { name: '3', exact: true }).click()
  await expect(show).toBeEnabled()
  await show.click()
  await expect(page.getByText('How did recall go?')).toBeVisible()
  await page.getByRole('button', { name: /^Good/ }).click()

  await finishReview(page) // one card is ours; earlier journeys may have left more
  await expect(page.getByText(/\d+ of \d+ due items reviewed/)).toBeVisible()
  await page.getByRole('button', { name: 'Continue the plan' }).click()
  await expect(page.getByRole('heading', { name: /^Learn: / })).toBeVisible()
  await expectServerBlock(request, { type: 'new_material', phase: 'teach' })
})

test('stop here keeps the session resumable from Home at the next block', async ({
  page,
  request,
  browser,
  baseURL,
}) => {
  await makeOneCardDue(request, 1)
  await startFromHome(page)
  await page.getByRole('button', { name: /^Review \(/ }).click()
  await expect(page.getByRole('button', { name: 'Show answer' })).toBeVisible()

  await page.getByRole('button', { name: 'Stop here (save progress)' }).click()
  await expect(page).toHaveURL(/\/recap$/)
  const afterStop = await currentSession(request)
  expect(afterStop?.id).toBeTruthy()
  expect(afterStop?.state?.block_status).toBe('ended')

  // a fresh context has no client state: Home must offer to resume the server's session
  const fresh = await browser.newContext({ baseURL: baseURL ?? undefined, reducedMotion: 'reduce' })
  try {
    const home = await fresh.newPage()
    await home.goto('/')
    await home.getByRole('button', { name: /^Resume session/ }).click()
    await expect(home.getByRole('heading', { name: 'Continue the plan?' })).toBeVisible()
    await home.getByRole('button', { name: /^Continue: / }).click()
    await expect(home.getByRole('heading', { name: /^Learn: / })).toBeVisible()
    await expectServerBlock(request, { type: 'new_material', phase: 'teach' })
    await home.reload()
    await expect(home.getByRole('heading', { name: /^Learn: / })).toBeVisible()
  } finally {
    await fresh.close()
  }
})
