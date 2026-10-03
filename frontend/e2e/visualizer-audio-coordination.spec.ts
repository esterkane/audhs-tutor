import { expect, test } from '@playwright/test'

test('visualizer monitoring yields to reading while silent analysis continues', async ({ page }) => {
  await page.route('**/api/preferences', (route) =>
    route.fulfill({ json: { values: { 'ui.sound': true, 'ui.reduced_motion': true }, specs: [] } }),
  )
  await page.route('**/api/voice/speak', () => {
    /* hold preparation until displaced */
  })
  await page.addInitScript(() => {
    class SilentContext {
      sampleRate = 48000
      currentTime = 0
      state = 'running'
      destination = {}
      createGain() {
        return { gain: { value: 0 }, connect() {} }
      }
      createOscillator() {
        return { type: 'sine', frequency: { value: 0 }, connect() {}, start() {}, stop() {} }
      }
      createAnalyser() {
        return {
          context: this,
          fftSize: 2048,
          smoothingTimeConstant: 0,
          get frequencyBinCount() {
            return this.fftSize / 2
          },
          getFloatTimeDomainData(a: Float32Array) {
            a.fill(0)
          },
          getFloatFrequencyData(a: Float32Array) {
            a.fill(-100)
          },
          connect() {},
        }
      }
      resume() {
        this.state = 'running'
        return Promise.resolve()
      }
      suspend() {
        this.state = 'suspended'
        return Promise.resolve()
      }
      close() {
        this.state = 'closed'
        return Promise.resolve()
      }
    }
    Object.defineProperty(window, 'AudioContext', { value: SilentContext })
  })
  await page.goto('/playground/visualizer')
  await page.evaluate(() => {
    const el = document.createElement('div')
    el.id = 'fixture'
    document.body.append(el)
  })
  await page.addScriptTag({ type: 'module', url: '/src/test/browser/visualizer-coordination.tsx' })
  await page.getByRole('button', { name: 'Listen to fixture', exact: true }).click()
  await expect(page.getByText('Preparing audio…', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByLabel('Learning step').selectOption('1')
  await page.getByRole('button', { name: 'Start test signal', exact: true }).click()
  const hear = page.getByRole('checkbox', { name: /Hear test signal at half volume/ })
  await expect(hear).toBeEnabled()
  await expect(page.getByText('Preparing audio…', { exact: true })).toBeVisible()
  await hear.check()
  await expect(
    page.getByText('Audio stopped because visualizer sound started.', { exact: true }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Listen to fixture', exact: true }).click()
  await expect(hear).not.toBeChecked()
  await expect(page.getByText(/Visualizer sound stopped because another reading started/)).toBeVisible()
  await expect(page.getByRole('button', { name: 'Pause test signal', exact: true })).toBeVisible()
  await hear.check()
  const shared = page.locator('header details').filter({ hasText: 'Audio controls' })
  await shared.locator('summary').click()
  await shared.getByRole('button', { name: 'Stop visualizer sound', exact: true }).click()
  await expect(hear).not.toBeChecked()
  await expect(page.getByRole('button', { name: 'Pause test signal', exact: true })).toBeVisible()
})
