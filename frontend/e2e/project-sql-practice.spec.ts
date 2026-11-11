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
  await area.getByRole('button', { name: 'Revisit the previous step' }).click()
  await expect(area.getByLabel('Final statement')).toHaveValue(' ABORT transaction ; ')
  expect(await projects()).toEqual(before)
  expect(writes).toEqual([])
})
