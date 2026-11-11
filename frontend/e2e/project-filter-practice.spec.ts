import { test, expect } from '@playwright/test'

test('filtered fixture preserves prediction and observation in learner-owned project evidence', async ({
  page,
}) => {
  await page.goto('/projects')
  await page.getByRole('button', { name: 'Open project: Qdrant', exact: true }).click()
  const evidence = page.getByLabel('Test evidence and observed results')
  await evidence.fill('My prior note.')
  await page.getByText('Practice filtered vector retrieval', { exact: true }).click()
  const prediction = page.getByLabel(/Predicted IDs in rank order/)
  await prediction.fill('B,C')
  await page.getByRole('button', { name: 'Run filtered search' }).press('Enter')
  await expect(page.getByText(/Compare your prediction with the observed order/)).toContainText(
    'C = 4, A = 3',
  )
  await page.getByRole('button', { name: 'Add run to project evidence' }).click()
  await expect(evidence).toHaveValue(
    /My prior note\.[\s\S]*My prediction: B,C[\s\S]*Observed IDs in rank order: C, A/,
  )
  await page.locator('summary').filter({ hasText: 'Change one condition' }).press('Enter')
  await page.getByLabel('Predicted order without the topic condition').fill('D,C,A')
  await page.getByRole('button', { name: 'Compare searches' }).press('Enter')
  await expect(page.getByText(/Without a topic condition:/)).toContainText('D = 5, C = 4, A = 3')
  await page.getByLabel('Predicted order with the new query').fill('C,A,D')
  await page.getByRole('button', { name: 'Check new query' }).press('Enter')
  await expect(page.getByText(/New query scores:/)).toContainText('A = 0, C = -1, D = -2')
  await page.getByRole('button', { name: 'Add comparison to project evidence' }).click()
  await expect(evidence).toHaveValue(/My prediction: C,A,D. Observed scores: A = 0, C = -1, D = -2/)
  await page.getByLabel('Topic filter').selectOption('traces')
  await expect(prediction).toBeEmpty()
  await prediction.fill('none')
  await page.getByRole('button', { name: 'Run filtered search' }).click()
  await expect(page.getByText(/Prediction matches/)).toContainText('Observed IDs: none')
  await page.getByRole('button', { name: 'Add run to project evidence' }).click()
  await expect(page.getByRole('button', { name: 'Add run to project evidence' })).toBeDisabled()
  await page
    .getByLabel('What I can explain and what remains uncertain')
    .fill('Tenant and topic restrict eligibility before comparing the surviving scores.')
  await page.getByRole('button', { name: 'Submit evidence for review' }).click()
  await expect(page.getByRole('status').filter({ hasText: 'does not certify mastery' })).toBeVisible()
  await page.reload()
  await expect(evidence).toHaveValue(
    /tenant blue, topic logs[\s\S]*tenant blue, topic traces[\s\S]*Observed IDs in rank order: none/,
  )
  await expect(evidence).toHaveValue(/Remove only the topic condition[\s\S]*New query \[-1, 2\]/)
  await expect(page.getByLabel('What I can explain and what remains uncertain')).toHaveValue(/eligibility/)
})
