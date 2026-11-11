import { test, expect } from '@playwright/test'

test('predict bool hits, compare explicit should count, submit evidence and resume', async ({ page }) => {
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Elasticsearch', exact: true }).click()
  const evidence = page.getByLabel('Test evidence and observed results')
  await evidence.fill('Initial relevance notes.')
  await page.getByText('Practice Boolean query matching', { exact: true }).click()
  const check = page.getByRole('button', { name: 'Check matching documents' })
  const append = page.getByRole('button', { name: 'Add query result to project evidence' })
  await page.getByRole('checkbox', { name: 'C', exact: true }).check()
  await check.press('Enter')
  await expect(page.getByText(/Compare your prediction/)).toContainText('Observed IDs: A, B.')
  await append.click()
  await page.getByLabel('Minimum should match').selectOption('1')
  await page.getByRole('checkbox', { name: 'A', exact: true }).check()
  await check.click()
  await expect(page.getByText(/Prediction matches/)).toContainText('Observed IDs: A.')
  await append.click()
  await expect(append).toBeDisabled()
  await page
    .getByLabel('What I can explain and what remains uncertain')
    .fill('B loses eligibility when the should match becomes mandatory.')
  await page.getByRole('button', { name: 'Submit evidence for review' }).click()
  await expect(page.getByText(/Project evidence submitted for review/)).toBeVisible()
  await page.reload()
  await expect(evidence).toHaveValue(
    /Initial relevance notes[\s\S]*predicted IDs: C. Observed IDs: A, B.[\s\S]*predicted IDs: A. Observed IDs: A./,
  )
})
