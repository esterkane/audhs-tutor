import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from '../e2e/helpers'

// Jupyter authenticates its local tab with a temporary credential.
test.use({ trace: 'off' })

test('run and reopen a project findings notebook from the accepted lesson', async ({
  page,
  request,
  context,
}) => {
  test.skip(process.env.AUDHS_TEST_JUPYTER !== '1', 'Requires installed local Jupyter')
  test.setTimeout(120_000)
  await endOpenSession(request)
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Supabase', exact: true }).click()
  const observation = 'Synthetic sample: one row of three was visible to the role.'
  await page.getByLabel('Test evidence and observed results').fill(observation)
  await page.getByRole('button', { name: 'Save project notes' }).click()
  await page.getByRole('button', { name: 'Create lesson draft from saved findings' }).click()
  await page.getByRole('button', { name: '1. Source' }).click()
  const title = 'Interpreting a visibility sample'
  await page.getByLabel('Material title', { exact: true }).fill(title)
  const socket = process.env.AUDHS_NOTEBOOK_PG_SOCKET
  if (socket && !/^\/tmp\/audhs-jupyter-pg-[A-Za-z0-9]{6}$/.test(socket))
    throw new Error('Expected disposable PostgreSQL socket')
  const code = socket
    ? `import psycopg
with psycopg.connect(host=${JSON.stringify(socket)}, dbname="postgres", user="notebook_reader", connect_timeout=3) as conn:
    conn.execute("SET TRANSACTION READ ONLY")
    result = conn.execute("SELECT current_user, item_id FROM public.practice_rows ORDER BY item_id").fetchall()
result`
    : 'sum([True, False, False])'
  const expected = socket ? "[('notebook_reader', 10)]" : '1'
  await page.getByLabel('Upload reference content (optional)').setInputFiles({
    name: 'sample.ipynb',
    mimeType: 'application/json',
    buffer: Buffer.from(
      JSON.stringify({
        nbformat: 4,
        nbformat_minor: 5,
        metadata: { kernelspec: { name: 'python3', language: 'python', display_name: 'Python 3' } },
        cells: [
          {
            cell_type: 'code',
            id: 'visibility',
            metadata: {},
            execution_count: null,
            outputs: [],
            source: [code],
          },
        ],
      }),
    ),
  })
  await expect(page.getByText('Open uploaded notebook locally', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: '3. Write' }).click()
  await page
    .getByLabel('Learning objective', { exact: true })
    .fill('Count visible rows in an observed sample.')
  await page.getByLabel('Explanation', { exact: true }).fill(observation)
  await page.getByLabel('Worked example', { exact: true }).fill('One true value contributes one visible row.')
  await page.getByLabel('Application question', { exact: true }).fill('How many rows were observed?')
  await page.getByLabel(/Success criteria/).fill('Reports the count from the sample.')
  await page.getByRole('button', { name: 'Next', exact: true }).click()
  const saved = page.waitForResponse((r) => r.request().method() === 'PUT' && r.url().includes('/drafts/'))
  await page.getByRole('button', { name: 'Save knowledge material' }).click()
  await expectOk(await saved)
  const published = page.waitForResponse((r) => r.url().endsWith('/publish'))
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  await expectOk(await published)
  const skills = (await (await request.get(API + '/api/skills')).json()).skills
  const skill = skills.find((s: { title: string }) => s.title === title)
  await page.goto('/?lesson=' + skill.id)
  const start = page.waitForResponse(
    (r) => r.request().method() === 'POST' && r.url().endsWith('/api/sessions'),
  )
  await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
  const session = await (await start).json()
  await expectOk(
    await request.post(API + '/api/plan/blocks/start', {
      data: {
        session_id: session.id,
        index: session.plan.findIndex((b: { type: string }) => b.type === 'new_material'),
      },
    }),
  )
  async function openFromReading() {
    await page.goto('/session')
    await page.getByText('Your notes and source references', { exact: true }).click()
    await page.getByText('Open uploaded notebook locally', { exact: true }).click()
    const link = page.getByRole('link', { name: 'Open prepared notebook in Jupyter' })
    if (!(await link.isVisible()))
      await page.getByRole('button', { name: 'Prepare and start notebook lab' }).click()
    await link.waitFor({ timeout: 30_000 })
    const opened = context.waitForEvent('page')
    await link.click()
    return opened
  }
  const lab = await openFromReading()
  const cell = lab.locator('.jp-Notebook:visible .jp-CodeCell').first()
  await expect(cell.locator('.cm-content')).toContainText(socket || code, { timeout: 30_000 })
  await expect(cell.locator('.jp-OutputArea-output')).toHaveCount(0)
  await expect(lab.getByRole('button', { name: /Python 3.*Idle/ })).toBeVisible({ timeout: 30_000 })
  await cell.locator('.cm-content').click()
  await lab.keyboard.press('Shift+Enter')
  await expect(cell.locator('.jp-OutputArea-output')).toHaveText(expected, { timeout: 30_000 })
  await lab.keyboard.press('Control+s')
  const contents = new URL(lab.url())
  contents.pathname = contents.pathname.replace('/lab/tree/', '/api/contents/')
  await expect
    .poll(async () => {
      const res = await lab.request.get(contents.href)
      return res.ok() && (await res.json()).content.cells[0].execution_count
    })
    .toBe(1)
  await lab.close()
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Supabase', exact: true }).click()
  await expect(page.getByLabel('Test evidence and observed results')).toHaveValue(observation)
  const reopened = await openFromReading()
  await expect(
    reopened.locator('.jp-Notebook:visible .jp-CodeCell').first().locator('.jp-OutputArea-output'),
  ).toHaveText(expected, { timeout: 30_000 })
  await reopened.close()
  await endOpenSession(request)
})
