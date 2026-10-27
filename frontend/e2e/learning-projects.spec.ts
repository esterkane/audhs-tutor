import { test, expect } from '@playwright/test'
import axe from 'axe-core'
import { API_URL } from '../playwright.config'

test('project notes, evidence and submission survive reload without certifying mastery', async ({ page, request }) => {
  await page.goto('/projects')
  await expect(page.getByRole('heading', { name: 'Knowledge projects', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: /^Open project:/ })).toHaveCount(6)
  await page.getByRole('button', { name: 'Open project: Supabase', exact: true }).click()
  await expect(page.getByRole('link', { name: 'Open the imported Supabase/PostgreSQL lab' })).toBeVisible()
  await page.getByLabel('My project notes').fill('Synthetic test: compare grants and row policies.')
  await expect(page.getByRole('button', { name: 'Submit evidence for review' })).toBeDisabled()
  await page.getByRole('button', { name: 'Save project notes' }).click()
  await expect(page.getByRole('status')).toContainText('Project writing saved')
  await page.reload()
  await expect(page.getByLabel('My project notes')).toHaveValue('Synthetic test: compare grants and row policies.')
  await page.getByLabel('Test evidence and observed results').fill('Synthetic fixture only; recorded outcomes belong here.')
  await page.getByLabel('What I can explain and what remains uncertain').fill('A grant and a row policy test different boundaries.')
  await page.getByRole('button', { name: 'Submit evidence for review' }).click()
  await expect(page.getByRole('status')).toContainText('does not certify mastery')
  await page.reload()
  await expect(page.getByLabel('Test evidence and observed results')).toHaveValue('Synthetic fixture only; recorded outcomes belong here.')
  await page.setViewportSize({ width:390, height:900 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.addScriptTag({ content:axe.source })
  expect(await page.evaluate(async () => (await (window as unknown as {axe:typeof axe}).axe.run('main')).violations)).toEqual([])
  const response = await request.get(API_URL + '/api/projects')
  expect(response.ok()).toBeTruthy()
  const rows = await response.json()
  expect(rows.find((row: { topic: string }) => row.topic === 'Supabase').status).toBe('submitted')
})

test('unconfigured Supabase project explains readiness without contacting a model', async ({ page }) => {
  await page.goto('/projects/supabase')
  await expect(page.getByRole('heading', { name: 'Supabase and PostgreSQL project', exact: true })).toBeVisible()
  await expect(page.getByRole('status')).toContainText('not configured')
  await expect(page.getByRole('button', { name: 'Check project readiness' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Back to knowledge projects' })).toHaveAttribute('href', '/projects')
})
