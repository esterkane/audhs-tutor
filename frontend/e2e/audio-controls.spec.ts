import { expect, test } from '@playwright/test'

test('audio controls persist across routes and remain usable on narrow screens', async ({ page }) => {
  await page.goto('/areas')
  const controls = page.locator('header details').filter({ hasText: 'Audio controls' })
  await controls.locator('summary').click()
  await controls.getByLabel('Audio volume').fill('0.25')
  await controls.getByLabel('Playback speed').selectOption('1.5')
  await controls.getByRole('button', { name: 'Mute', exact: true }).click()
  await expect(controls.getByRole('button', { name: 'Test sound' })).toBeDisabled()
  await page.getByRole('link', { name: 'Audio visualizer', exact: true }).click()
  await expect(controls.getByLabel('Audio volume')).toHaveValue('0.25')
  await expect(controls.getByLabel('Playback speed')).toHaveValue('1.5')
  await page.reload()
  await controls.locator('summary').click()
  await expect(controls.getByRole('button', { name: 'Unmute', exact: true })).toBeVisible()
  await page.setViewportSize({ width: 390, height: 844 })
  await controls.getByRole('button', { name: 'Unmute', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(controls.getByRole('button', { name: 'Test sound' })).toBeEnabled()
  // Headless browser verifies output lifecycle, not physical headphone audibility.
  await controls.getByRole('button', { name: 'Test sound' }).click()
  await expect(controls.getByRole('status')).toContainText('Test finished')
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('requested reading shows preparation, silence settings and completion', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 900 })
  await page.addInitScript(() =>
    localStorage.setItem('audio-settings-v1', JSON.stringify({ muted: true, volume: 0.5, rate: 1 })),
  )
  await page.route('**/local-learning/program.json', (route) =>
    route.fulfill({
      json: {
        title: 'Local study',
        courses: [
          {
            id: 'audio',
            title: 'Audio example',
            project: 'Compare',
            status: 'Fixture',
            sections: [
              {
                id: 'first',
                title: 'Inspect the data',
                explanation: 'Compare missing values.',
                task: 'Count rows.',
                question: 'Why compare groups?',
                hint: 'Think of representation.',
                criteria: 'Explain changes.',
                source: 'Synthetic fixture',
              },
            ],
          },
        ],
      },
    }),
  )
  let release!: () => void
  const held = new Promise<void>((resolve) => {
    release = resolve
  })
  await page.route('**/api/voice/speak', async (route) => {
    await held
    await route.fulfill({ json: { pcm16_b64: Buffer.alloc(48000).toString('base64'), sample_rate: 24000 } })
  })
  await page.goto('/programs')
  const listen = page.getByRole('button', { name: 'Listen to explanation', exact: true })
  await listen.click()
  await expect(page.getByText('Preparing audio…', { exact: true })).toBeVisible()
  await expect(page.getByText(/Audio is muted/).first()).toBeVisible()
  await page.getByRole('button', { name: 'Pause audio', exact: true }).click()
  await expect(page.getByText('Audio paused. Resume continues from the same position.')).toBeVisible()
  release()
  await expect(page.getByRole('button', { name: 'Resume audio', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Resume audio', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Audio finished.', { exact: true })).toBeVisible()
  await listen.click()

  await page.getByRole('button', { name: 'Stop audio', exact: true }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Audio stopped. Listen again starts from the beginning.')).toBeVisible()
  release()
  await listen.click()
  await expect(page.getByText('Audio finished.', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
