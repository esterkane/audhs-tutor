import { expect, test } from '@playwright/test'

test('playground runs locally, keeps separate drafts and identifies stale output', async ({ page }) => {
  await page.goto('/playground')
  await expect(page.getByRole('heading', { name: 'Coding playground' })).toBeVisible()
  await page.getByRole('combobox', { name: 'Workspace', exact: true }).selectOption('worked')
  await page.getByRole('button', { name: 'Run code' }).click()
  await expect(page.getByText("['Ada', 'Lin']", { exact: true })).toBeVisible({ timeout: 45000 })
  await page.getByText('Editor and runtime options', { exact: true }).click()
  await page.getByRole('button', { name: 'Use plain editor' }).click()
  const editor = page.getByLabel(/Python code/)
  await editor.fill('print("saved experiment")')
  await expect(page.getByText(/output is from earlier code/)).toBeVisible()
  await page.getByRole('combobox', { name: 'Workspace', exact: true }).selectOption('scratch')
  await expect(page.getByLabel(/Python code/)).not.toHaveValue('print("saved experiment")')
  await page.getByRole('combobox', { name: 'Workspace', exact: true }).selectOption('worked')
  await expect(page.getByLabel(/Python code/)).toHaveValue('print("saved experiment")')
  await page.reload()
  await page.getByRole('combobox', { name: 'Workspace', exact: true }).selectOption('worked')
  await expect(page.getByLabel(/Python code/)).toHaveValue('print("saved experiment")')
  await page.getByRole('button', { name: 'Run code' }).click()
  await expect(page.getByText('saved experiment', { exact: true })).toBeVisible({ timeout: 45000 })
})

for (const width of [1280, 390]) {
  test(`playground tutor can stop and retry without losing a question at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 })
    await page.route('**/api/sessions/current', (route) => route.fulfill({ json: { id: 'fixture-session' } }))
    let release: (() => void) | undefined
    let requests = 0
    await page.route('**/api/playground/tutor', async (route) => {
      requests += 1
      const first = requests === 1
      if (first)
        await new Promise<void>((resolve) => {
          release = resolve
        })
      await route.fulfill({
        json: {
          text: first ? 'Old discarded answer' : 'Current explanation for your code.',
          model: 'fixture',
          route: 'fake',
          source_note: 'Synthetic guidance',
          turn_id: 'fixture',
        },
      })
    })
    await page.goto('/playground')
    const input = page.getByRole('textbox', { name: 'Ask about your code', exact: true })
    await input.fill('Explain the next line.')
    const send = page.getByRole('button', { name: 'Send question', exact: true })
    await send.click()
    await expect(page.getByText(/Waiting [1-9]\d* seconds?/)).toBeVisible()
    const stop = page.getByRole('button', { name: 'Stop waiting', exact: true })
    await stop.focus()
    await page.keyboard.press('Enter')
    await expect(send).toBeEnabled()
    await expect(input).toHaveValue('Explain the next line.')
    await expect(page.getByRole('status', { name: 'Tutor response status' })).toContainText(
      'Response stopped',
    )
    release!()
    await send.click()
    await expect(page.getByRole('status', { name: 'Tutor response status' })).toHaveText(
      'Tutor response ready.',
    )
    await expect(page.getByText('Current explanation for your code.', { exact: true })).toBeVisible()
    await expect(page.getByText('Old discarded answer', { exact: true })).toHaveCount(0)
    expect(requests).toBe(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
