import { expect, test } from '@playwright/test'
import { API } from './helpers'

test('explicit key save clears the field and keeps authoring mode and budget unchanged', async ({ page, request }) => {
  const before = await (await request.get(`${API}/api/authoring/setup`)).json()
  let saves = 0
  await page.route('**/api/authoring/key', async route => {
    expect(route.request().postDataJSON()).toEqual({ key: 'synthetic-browser-secret' })
    saves++
    await route.fulfill({ json: { ...before, key_configured: true } })
  })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto('/curriculum')
  await page.getByText('Authoring setup: OpenAI or local', { exact: true }).click()
  const input = page.getByLabel('OpenAI API key', { exact: true })
  const save = page.getByRole('button', { name: 'Save API key', exact: true })
  await expect(save).toBeDisabled()
  await input.fill('synthetic-browser-secret')
  await expect(page.getByText(/Key entered but not saved/)).toBeVisible()
  await save.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('API key saved on this machine. No model request was made.')).toBeVisible()
  await expect(input).toHaveValue('')
  await expect(save).toBeDisabled()
  expect(saves).toBe(1)
  const after = await (await request.get(`${API}/api/authoring/setup`)).json()
  expect(after).toEqual(before) // intercepted secret never reached the sandbox or a provider
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
})
