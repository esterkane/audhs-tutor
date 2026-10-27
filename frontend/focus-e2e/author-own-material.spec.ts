import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { execFileSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { API_URL } from '../playwright.config'

const root = resolve(import.meta.dirname, '../..')
test.beforeAll(async ({ request }) => {
  expect((await request.get(API_URL + '/api/learner/me')).ok()).toBeTruthy()
  const destination = mkdtempSync(resolve(tmpdir(), 'audhs-focus-map-'))
  execFileSync(
    resolve(root, 'backend/.venv/bin/python'),
    [
      resolve(root, 'scripts/reset_learning_focus.py'),
      '--apply',
      '--backup',
      resolve(destination, 'before-reset.db'),
    ],
    {
      cwd: resolve(root, 'backend'),
      env: {
        ...process.env,
        DATABASE_URL: 'sqlite+aiosqlite:///' + resolve(root, 'data/focus-sandbox.db'),
        ANTHROPIC_API_KEY: '',
        OPENAI_API_KEY: '',
        DAILY_BUDGET_USD: '0',
      },
      timeout: 20000,
    },
  )
})

test('fresh focused upload to authored lesson, reading, notes, feedback and resume', async ({
  page,
  request,
}) => {
  page.setDefaultTimeout(15000)
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'learning-companion:context:v1',
      JSON.stringify({
        version: 1,
        active: {
          id: '11111111-1111-1111-1111-111111111111',
          text: 'Synthetic retired course snapshot',
          title: 'Historical snapshot',
          path: '/programs?course=retired',
        },
        draft: null,
        previous: null,
      }),
    )
  })
  const skillsBefore = await request.get(API_URL + '/api/skills')
  expect((await skillsBefore.json()).skills).toEqual([])
  const areas = await request.get(API_URL + '/api/areas')
  expect((await areas.json()).areas).toHaveLength(6)
  await page.goto('/map')
  await expect(page.getByRole('status')).toContainText('No skills are available yet')
  await expect(page.getByRole('button', { name: 'Reopen learning companion', exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => sessionStorage.getItem('learning-companion:context:v1'))).toContain(
    'Synthetic retired course snapshot',
  )
  await page.goto('/projects')
  await expect(page.getByRole('button', { name: /^Open project:/ })).toHaveCount(6)
  await expect(page.getByRole('link', { name: /Audio visualizer|Guitar/i })).toHaveCount(0)
  await page.goto('/curriculum?topic=supabase')
  await page.getByLabel('Material title', { exact: true }).fill('Supabase grants and row visibility')
  await expect(page.getByRole('combobox', { name: 'Technology', exact: true })).toHaveValue('supabase')
  const source =
    'Table privileges and row visibility are separate checks. With the required SELECT privilege, a row policy that admits no rows normally gives an empty result. A missing table privilege may give permission denied. Test the application role rather than the table owner.'
  const upload = page.waitForResponse((response) => response.url().endsWith('/knowledge-material/uploads'))
  await page.getByLabel('Upload reference content (optional)').setInputFiles({
    name: 'new-notes-'.repeat(30) + '.md',
    mimeType: 'text/markdown',
    buffer: Buffer.from(source),
  })
  expect((await upload).ok()).toBeTruthy()
  await expect(page.getByLabel('Your notes and selected source content')).toHaveValue(source)
  await page.getByRole('button', { name: '2. Research', exact: true }).click()
  await page.getByLabel('Topic to investigate').fill('Supabase grants and row visibility')
  await page.getByRole('button', { name: 'Use notes as passage', exact: true }).click()
  await page.getByRole('button', { name: 'Prepare research questions', exact: true }).click()
  await page
    .getByLabel('My findings', { exact: true })
    .fill('These are different boundaries; an empty result is not a table permission-denied error.')
  await page.getByRole('button', { name: '3. Write', exact: true }).click()
  const explanation =
    'A table privilege determines whether the application role may perform an operation. Row policies restrict which rows it can read. For an ordinary SELECT, a policy admitting no rows normally returns zero rows when the required privileges exist. This alone does not explain a table permission-denied error.'
  await page.getByLabel('My knowledge section', { exact: true }).fill(explanation)
  await page.getByRole('button', { name: 'Add section to explanation', exact: true }).click()
  const saved = page.waitForResponse(
    (response) =>
      response.url().endsWith('/knowledge-material/drafts') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  expect((await saved).ok()).toBeTruthy()
  await expect(page).toHaveURL(/draft=/)
  await page.reload()
  await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(explanation)
  await page.getByRole('button', { name: '4. Review', exact: true }).click()
  await page.locator('summary').filter({ hasText: 'Shape a lesson (optional)' }).click()
  await page
    .getByLabel('Learning objective', { exact: true })
    .fill('Distinguish missing table privileges from row-policy filtering.')
  await page
    .getByLabel('Worked example', { exact: true })
    .fill(
      'An application role has SELECT on a table, but no rows pass its policy: an ordinary SELECT returns zero rows. If SELECT is not granted, the database can instead reject table access.',
    )
  await page
    .getByLabel('Application question', { exact: true })
    .fill(
      'A role can SELECT a table, but its policy admits no rows. What result is normally expected, and which role should you use to test it?',
    )
  await page.getByRole('textbox', { name: /Success criteria/ })
    .fill(`Expects an empty result for the stated ordinary SELECT.
Tests the actual application role rather than the table owner.`)
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Activate lessons', exact: true })).toBeEnabled()
  const activation = page.waitForResponse(
    (response) => response.url().endsWith('/publish') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  expect((await activation).ok()).toBeTruthy()
  const skills = (await (await request.get(API_URL + '/api/skills')).json()).skills
  const skill = skills.find((row: { title: string }) => row.title === 'Supabase grants and row visibility')
  expect(skill).toBeTruthy()
  await page.goto('/?lesson=' + skill.id)
  await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
  await expect(page).toHaveURL(/\/session$/)
  const current = await (await request.get(API_URL + '/api/sessions/current')).json()
  await request.post(API_URL + '/api/plan/blocks/start', {
    data: {
      session_id: current.id,
      index: current.plan.findIndex((row: { type: string }) => row.type === 'new_material'),
    },
  })
  await page.goto('/session')
  await expect(page.getByRole('navigation', { name: 'Learning path' })).toContainText(
    'Supabase grants and row visibility',
  )
  await page.getByRole('button', { name: 'Next section', exact: true }).click()
  await page
    .getByLabel('Your notes for this section (optional)')
    .fill('I will compare table privileges and row filtering separately.')
  await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
  await page.getByRole('button', { name: 'Continue', exact: true }).click()
  await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue(
    'I will compare table privileges and row filtering separately.',
  )
  await page.setViewportSize({ width: 390, height: 900 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  await page.addScriptTag({ content: axe.source })
  expect(
    await page.evaluate(
      async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations,
    ),
  ).toEqual([])
  await page.getByRole('button', { name: 'Try this lesson', exact: true }).click()
  await page.getByLabel('Your answer', { exact: true }).fill("I don't know")
  await page.getByRole('button', { name: 'Check my answer', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Feedback on your answer', exact: true })).toBeVisible()
  await page.goto('/recap')
  await page
    .getByLabel('One line for next time (optional)')
    .fill('Compare grants and RLS with a disposable fixture.')
  await page.getByRole('button', { name: 'Save and finish session', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Session saved', exact: true })).toBeVisible()
})
