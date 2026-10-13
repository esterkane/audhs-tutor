import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { API, endOpenSession, expectOk } from './helpers'

// Only the starting saved answer is a fixture. Draft, activation and session use real HTTP/storage.
for (const width of [390, 1280]) test(`saved answer becomes an explicitly selected private lesson ${width}`, async ({ page, request }, info) => {
  await endOpenSession(request)
  const root = fileURLToPath(new URL('../../', import.meta.url))
  const id = execFileSync('uv', ['run', '--directory', 'backend', 'python', '-c', `
import asyncio, os, pathlib, sys, uuid
from sqlalchemy import select
from app.db.models import LearnerProfile, TutorAnswer
from app.db.session import make_engine, make_session_factory
root = pathlib.Path(sys.argv[1]).resolve()
p = root / 'data' / 'sandbox.db'
assert p.is_file() and not p.is_symlink() and p.resolve() == p
assert pathlib.Path(os.environ.get('SANDBOX_DB', './data/sandbox.db')) == pathlib.Path('data/sandbox.db')
async def main():
    engine = make_engine('sqlite+aiosqlite:///' + str(p))
    try:
        async with make_session_factory(engine)() as db:
            learner = await db.scalar(select(LearnerProfile).order_by(LearnerProfile.created_at))
            identity = 'e2e-' + str(uuid.uuid4())
            db.add(TutorAnswer(id=identity, learner_id=learner.id, turn_id=identity, surface='ask', fingerprint=identity,
                request_json={'question':'How do I protect held-out data?'},
                text='Fit preprocessing on training records only. Apply the saved transform to held-out records.',
                metadata_json={'sources':[], 'source_text_hashes':{}, 'origin_status':'unknown'}))
            await db.commit()
            print(identity)
    finally:
        await engine.dispose()
asyncio.run(main())
`, root], { cwd: root, encoding: 'utf8' }).trim()
  try {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(`/ask?answer=${id}`)
    await page.locator('summary').filter({ hasText: 'Create lesson draft (optional)' }).click()
    await page.getByLabel('Lesson title', { exact: true }).fill('Private preprocessing journey')
    await page.getByLabel('What should the learner be able to do?').fill('Protect held-out data when fitting preprocessing.')
    await page.getByRole('button', { name: 'Use answer as explanation' }).click()
    await page.getByRole('textbox', { name: 'Worked example', exact: true }).fill('Training ages 20 and 40 give median 30. Reuse 30 for held-out rows.')
    await page.getByLabel('Application question', { exact: true }).fill('Which records should determine the imputation median? Explain why.')
    await page.getByLabel('Grading criteria').fill('Use observed training ages only.\nApply the same median to both sets.')
    await page.getByRole('button', { name: 'Save private lesson draft', exact: true }).click()
    await page.getByRole('link', { name: 'Open saved lesson draft' }).click()
    await expect(page.getByRole('heading', { name: 'Private preprocessing journey', exact: true })).toBeVisible()
    await page.getByRole('checkbox', { name: /I reviewed this saved version/ }).check()
    const activated = page.waitForResponse(r => r.url().endsWith('/api/lesson-activations/commands') && r.request().method() === 'POST')
    await page.getByRole('button', { name: 'Activate private lessons', exact: true }).click()
    const response = await activated
    await expectOk(response)
    const receipt = await response.json()
    await expect(page.getByText('Your private lesson is active.', { exact: true })).toBeVisible()
    await page.reload()
    await expect(page.getByText('Your private lesson is active.', { exact: true })).toBeVisible()
    await page.getByRole('link', { name: 'Open this lesson' }).click()
    await expect(page).toHaveURL(new RegExp(`\\?lesson=${receipt.skill_ids[0]}$`))
    await expect(page.getByRole('heading', { name: 'Learn: Private preprocessing journey' })).toBeVisible()
    const start = page.getByRole('button', { name: 'Start this lesson', exact: true })
    await start.focus(); await page.keyboard.press('Enter')
    await expect.poll(async () => (await (await request.get(`${API}/api/sessions/current`)).json())?.state?.skill_id).toBe(receipt.skill_ids[0])
    await page.reload()
    await expect(page.getByText('Private preprocessing journey', { exact: false }).first()).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const session = await (await request.get(`${API}/api/sessions/current`)).json()
    // Enter the teaching block directly; movement/plan choices have separate journeys.
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index: session.plan.findIndex((b: { type: string }) => b.type === 'new_material') } }))
    let generations = 0
    page.on('request', r => { if (r.url().endsWith('/api/tutor/stream')) generations++ })
    await page.reload()
    await expect(page.getByText('Fit preprocessing on training records only.', { exact: false })).toBeVisible()
    await page.getByRole('combobox', { name: 'Choose a section' }).selectOption({ label: '2. Worked example 1' })
    await expect(page.getByText('Training ages 20 and 40 give median 30.', { exact: false })).toBeVisible()
    await page.getByLabel('Your notes for this section (optional)').fill('Reuse the training median.')
    await page.reload()
    await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue('Reuse the training median.')
    await page.getByRole('button', { name: 'Let me try', exact: true }).focus()
    await page.keyboard.press('Enter')
    // ASCII apostrophe matches the explicit deterministic abstention contract.
    await page.getByLabel('Your answer', { exact: true }).fill("I don't know")
    const checked = page.waitForResponse(r => r.url().endsWith('/api/assess/attempt'))
    await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
    const checkedResponse = await checked
    await expectOk(checkedResponse)
    expect((await checkedResponse.json()).score).toBe(0)
    await expect(page.getByRole('heading', { name: 'Feedback on your answer' })).toBeVisible()
    await page.getByRole('button', { name: 'Revisit the explanation', exact: true }).click()
    await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue('Reuse the training median.')
    expect(generations).toBe(0)
    await page.addScriptTag({ content: axe.source })
    expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
    await expect(page.getByText('No explanation has been prepared yet.', { exact: true })).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('private-lesson-reading.png'), fullPage: true })
    await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; document.documentElement.style.fontSize = '200%' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: info.outputPath('private-lesson-reading-dark-zoom.png'), fullPage: true })
  } finally {
    await endOpenSession(request)
  }
})
