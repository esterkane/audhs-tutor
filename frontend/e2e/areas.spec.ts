import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'

test('areas can be renamed and selected as a goal without activating lessons', async ({ page, request }) => {
  await page.goto('/areas')
  await expect(page.getByRole('heading', { name: 'Learning areas', exact: true })).toBeVisible()
  const initialized = page.waitForResponse((response) =>
    new URL(response.url()).pathname === '/api/areas/initialize' && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Suggest areas from my material' }).click()
  expect((await initialized).ok()).toBe(true)
  const catalog = await (await request.get(`${API_URL}/api/areas`)).json()
  const area = catalog.areas.find((a: { slug: string }) => a.slug === 'rag')
  expect(area, 'Initialized catalog includes the retrieval area').toBeDefined()
  await page.getByLabel('Area to review').selectOption(area.id)
  await page.route('**/api/answers?*', async (route) => {
    const query = new URL(route.request().url()).searchParams
    expect(query.get('area_id')).toBe(area.id)
    expect(query.has('surface')).toBe(false)
    await route.fulfill({ json: { items: [], next_cursor: null } })
  })
  await page.getByText('Saved answers for this learning area').click()
  await expect(page.getByText(/No saved replies for this learning area/)).toBeVisible()
  await expect(page.getByRole('link', { name: 'Browse all answers for this learning area' })).toHaveAttribute(
    'href',
    `/answers?area_id=${area.id}`,
  )
  await page.getByText('Saved answers for this learning area').click()
  await page.getByText('Edit area name and matching terms', { exact: true }).click()
  await page.getByLabel('Area name', { exact: true }).fill('My retrieval practice')
  await page.getByRole('button', { name: 'Save area', exact: true }).click()
  await expect(page.getByRole('status')).toHaveText('Area saved.')
  await page.getByText('Your feedback and question preferences', { exact: true }).click()
  const preference = page.getByRole('checkbox', { name: 'More concrete application and debugging questions' })
  await preference.click()
  await expect(preference).toBeChecked()
  await page.reload()
  await page.getByText('Your feedback and question preferences', { exact: true }).click()
  await expect(preference).toBeChecked()
  await preference.click()
  await page.goto('/')
  await page.getByRole('combobox', { name: 'Knowledge area', exact: true }).selectOption(area.id)
  await expect(page.getByRole('combobox', { name: 'Goal', exact: true })).toHaveCount(0)
  await page.getByRole('combobox', { name: 'Knowledge area', exact: true }).selectOption('')
  await expect(page.getByRole('combobox', { name: 'Goal', exact: true })).toBeEnabled()
})
