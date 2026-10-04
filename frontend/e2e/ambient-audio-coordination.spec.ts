import { expect, test } from '@playwright/test'

test('ambient sound and output tests replace each other through shared controls', async ({ page }) => {
  await page.route('**/api/preferences', (route) =>
    route.fulfill({ json: { values: { 'ui.ambient': 'brown' }, specs: [] } }),
  )
  await page.addInitScript(() => {
    // Silent fake nodes: this checks app ownership, not device output.
    class SilentContext {
      sampleRate = 8
      currentTime = 0
      destination = {}
      createBuffer() {
        return { getChannelData: () => new Float32Array(32) }
      }
      createGain() {
        return { gain: { value: 0 }, connect() {} }
      }
      createBufferSource() {
        return {
          connect(gain: unknown) {
            return gain
          },
          start() {},
          stop() {},
        }
      }
      createOscillator() {
        return {
          frequency: { value: 0 },
          connect(gain: unknown) {
            return gain
          },
          start() {},
          stop() {},
          onended: null,
        }
      }
      resume() {
        return Promise.resolve()
      }
      close() {
        return Promise.resolve()
      }
    }
    Object.defineProperty(window, 'AudioContext', { value: SilentContext })
  })
  await page.goto('/together')
  const shared = page.locator('header details').filter({ hasText: 'Audio controls' })
  await shared.locator('summary').click()
  await page.getByRole('button', { name: 'Play brown noise', exact: true }).click()
  await expect(page.locator('header').getByRole('button', { name: 'Stop ambient sound' })).toBeVisible()
  await shared.getByRole('button', { name: 'Test sound', exact: true }).click()
  await expect(
    page.getByText('Brown noise stopped for a sound test. Choose Play brown noise to start again.'),
  ).toBeVisible()
  await expect(page.locator('header').getByRole('button', { name: 'Stop ambient sound' })).toHaveCount(0)
  await expect(page.locator('header').getByRole('button', { name: 'Stop sound test' })).toBeVisible()
  await page.getByRole('button', { name: 'Play brown noise', exact: true }).click()
  await expect(
    shared.getByText('Sound test stopped because brown noise started.', { exact: true }),
  ).toBeVisible()
  await page.locator('header').getByRole('button', { name: 'Stop ambient sound' }).click()
  await expect(page.getByRole('button', { name: 'Play brown noise', exact: true })).toBeVisible()
  await expect(page.locator('header').getByRole('button', { name: 'Stop ambient sound' })).toHaveCount(0)
})
