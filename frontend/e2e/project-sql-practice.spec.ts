import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'

test('role-check practice moves from arranging to completing to independent writing', async ({
  page,
  request,
}) => {
  const projects = async () => (await request.get(API_URL + '/api/projects')).json()
  const before = await projects()
  const project = before.find((row: { slug: string }) => row.slug === 'supabase-postgres-support')
  const writes: string[] = []
  page.on('request', (r) => {
    if (r.url().includes('/api/') && r.method() !== 'GET') writes.push(r.url())
  })
  await page.goto('/projects?project=' + project.id)
  const open = () => page.getByText('Practice a role check (optional)', { exact: true }).click()
  await open()
  const area = page.getByRole('region', { name: 'SQL role practice' })
  await area.getByRole('button', { name: 'Check order' }).click()
  await expect(area.getByRole('status')).toContainText('Start the transaction before changing role')
  for (const text of ['BEGIN READ ONLY;', 'SET LOCAL ROLE authenticated;']) {
    const up = area.getByRole('button', { name: 'Move ' + text + ' up', exact: true })
    await up.press('Enter')
    await up.press('Enter')
  }
  await area.getByRole('button', { name: 'Check order' }).press('Enter')
  await area.getByLabel('Final statement').fill('commit;')
  await area.getByRole('button', { name: 'Check final statement' }).click()
  await expect(area.getByRole('status')).toContainText('asks you to roll back')
  await area.getByLabel('Final statement').fill(' ABORT transaction ; ')
  await area.getByRole('button', { name: 'Check final statement' }).press('Enter')
  const query = 'BEGIN READ ONLY; SET LOCAL ROLE authenticated; SELECT current_user; ABORT;'
  await area.getByLabel('Your SQL').fill(query)
  await page.reload()
  await open()
  await expect(area.getByLabel('Your SQL')).toHaveValue(query)
  await area.getByRole('button', { name: 'Compare with an example' }).click()
  await expect(area.getByText(/Checking the effective role alone/)).toBeVisible()
  const transfer = area.locator('summary').filter({ hasText: 'Try a different role and transaction ending' })
  await transfer.press('Enter')
  const compareTransfer = area.getByRole('button', { name: 'Compare the new role check' })
  await expect(compareTransfer).toBeDisabled()
  await expect(area.getByText(/Inside the transaction the effective role is/)).toHaveCount(0)
  const transferSql =
    'BEGIN READ ONLY; SET LOCAL ROLE reporting_reader; SELECT current_user, current_user = session_user; COMMIT; SELECT current_user = session_user;'
  await area.getByLabel('SQL for the new situation').fill(transferSql)
  await area.getByLabel('Predicted results before and after commit').fill('I predict false both times.')
  await compareTransfer.press('Enter')
  await expect(area.getByText(/Inside the transaction the effective role is/)).toContainText(
    'equality is true',
  )
  await page.reload()
  await open()
  await transfer.press('Enter')
  await expect(area.getByLabel('SQL for the new situation')).toHaveValue(transferSql)
  await expect(area.getByLabel('Predicted results before and after commit')).toHaveValue(
    'I predict false both times.',
  )
  await expect(area.getByText(/Your SQL is saved for comparison and is ungraded/)).toBeVisible()
  await area.getByRole('button', { name: 'Revisit the previous step' }).click()
  await expect(area.getByLabel('Final statement')).toHaveValue(' ABORT transaction ; ')
  await area.getByLabel('Final statement').fill('COMMIT;')
  await area.getByRole('button', { name: 'Check final statement' }).click()
  await expect(area.getByRole('status')).toContainText('asks you to roll back')
  await page.reload()
  await open()
  await expect(area.getByLabel('Final statement')).toHaveValue('COMMIT;')
  await area.getByLabel('Final statement').fill('ROLLBACK;')
  await area.getByRole('button', { name: 'Check final statement' }).click()
  await expect(area.getByLabel('Your SQL')).toHaveValue(query)
  await transfer.press('Enter')
  await expect(area.getByLabel('SQL for the new situation')).toHaveValue(transferSql)
  await expect(area.getByLabel('Predicted results before and after commit')).toHaveValue(
    'I predict false both times.',
  )
  expect(await projects()).toEqual(before)
  expect(writes).toEqual([])
})

test('an older saved SQL exercise can start the new transfer step', async ({ page, request }) => {
  const projects = await (await request.get(API_URL + '/api/projects')).json()
  const project = projects.find((row: { slug: string }) => row.slug === 'supabase-postgres-support')
  await page.goto('/projects?project=' + project.id)
  await page.evaluate((id: string) => {
    const draftId = 'sql-role-practice-v1:' + id
    const text = JSON.stringify({
      order: [0, 1, 2, 3], stage: 2, ending: 'ROLLBACK;', query: 'SELECT current_user;', compared: true,
    })
    sessionStorage.setItem('curriculum-edit:v1:' + draftId, JSON.stringify({
      version: 1, draftId, baseVersion: 1, text, baseText: '{}', savedAt: new Date().toISOString(),
    }))
  }, project.id)
  await page.reload()
  await page.getByText('Practice a role check (optional)', { exact: true }).click()
  await expect(page.getByLabel('Your SQL')).toHaveValue('SELECT current_user;')
  await page.getByText('Try a different role and transaction ending', { exact: true }).click()
  await expect(page.getByLabel('SQL for the new situation')).toHaveValue('')
  await expect(page.getByRole('button', { name: 'Compare the new role check' })).toBeDisabled()
})
