import { expect, test, type APIRequestContext } from '@playwright/test'
import {
  API,
  currentSession,
  endOpenSession,
  expectOk,
  expectServerBlock,
  finishReview,
  freshDeterministicSkill,
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

/** Make a fresh deterministic card due without depending on other journeys' attempts. */
async function makeOneCardDue(request: APIRequestContext) {
  const started = await request.post(`${API}/api/sessions`, {
    data: { mode: 'steady', energy: 3, socratic: false },
  })
  await expectOk(started)
  const session = (await started.json()) as { id: string }
  const skillId = freshDeterministicSkill()
  const next = await request.get(`${API}/api/assess/next?session_id=${session.id}&skill_id=${skillId}`)
  await expectOk(next)
  const { item } = (await next.json()) as {
    item: { id: string; kind: string; content_version: string } | null
  }
  expect(item).not.toBeNull()
  expect(['mcq', 'cloze'], 'deterministically graded kinds only (no local model in CI)').toContain(item!.kind)
  const attempt = await request.post(`${API}/api/assess/attempt`, {
    data: {
      session_id: session.id,
      assessment_id: item!.id,
      content_version: item!.content_version,
      answer: 'no idea',
      confidence_pre: 1,
    },
  })
  await expectOk(attempt)
  const far = new Date(Date.now() + 30 * 86_400_000).toISOString()
  const due = (await (
    await request.get(`${API}/api/review/due?session_id=${session.id}&as_of=${far}&all=true`)
  ).json()) as { items: Array<{ item_id: string; skill_id: string; content_version: string }> }
  const mine = due.items.find((d) => d.skill_id === skillId)
  expect(mine, 'the attempt created a review card for this skill').toBeTruthy()
  const past = new Date(Date.now() - 3 * 86_400_000).toISOString()
  const rated = await request.post(`${API}/api/review/${mine!.item_id}?as_of=${past}`, {
    data: { session_id: session.id, rating: 1, content_version: mine!.content_version },
  })
  await expectOk(rated)
  await endOpenSession(request)
}

test.beforeEach(async ({ request }) => endOpenSession(request))
test.afterEach(async ({ request }) => endOpenSession(request))

test('a reload at every block boundary lands on the block the server owns', async ({ page, request }) => {
  await startFromHome(page)
  await expect(page.getByRole('heading', { name: /Choose where to begin|Which first/ })).toBeVisible()
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

test('review offers optional confidence before revealing, then the plan continues', async ({
  page,
  request,
}) => {
  await makeOneCardDue(request)
  await startFromHome(page)
  await page.getByRole('button', { name: /^Review \(/ }).click()

  await page.getByText('Confidence (optional)', { exact: true }).click()
  const confidence = page.getByRole('group', { name: /how sure are you/i })
  await expect(confidence).toBeVisible()
  const show = page.getByRole('button', { name: 'Show answer' })
  await expect(show).toBeEnabled()
  await confidence.getByRole('button', { name: '3', exact: true }).click()
  await expect(show).toBeEnabled()
  await show.click()
  await expect(page.getByText('How did recall go?')).toBeVisible()
  await page.getByRole('button', { name: /^Good/ }).click()

  await finishReview(page) // one card is ours; earlier journeys may have left more
  await expect(page.getByText(/Nothing is due right now|cards reviewed in this session/)).toBeVisible()
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
  await makeOneCardDue(request)
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
    await home.getByRole('button', { name: /^Resume previous session/ }).click()
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
