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
  await expect(page.getByLabel('What I can explain and what remains uncertain')).toHaveValue(/eligibility/)
})
