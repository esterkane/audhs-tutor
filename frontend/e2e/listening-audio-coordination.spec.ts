import { expect, test } from '@playwright/test'

test('a listening clip yields to a reading and resumes at the same position', async ({ page }) => {
  await page.route('**/api/listening/lessons/clip', (route) =>
    route.fulfill({
      json: {
        document_id: 'clip',
        title: 'Local clip',
        media_url: '/fixture-audio',
        language: 'en',
        next_index: 0,
        sections: [{ chunk_id: 'chunk', t_start: 0, t_end: 20, text: 'Synthetic transcript', index: 0 }],
      },
    }),
  )
  await page.route('**/api/voice/speak', () => {
    /* remain pending until displaced */
  })
  await page.addInitScript(() => {
    HTMLMediaElement.prototype.play = function () {
      return Promise.resolve()
    }
    HTMLMediaElement.prototype.pause = function () {
      this.dispatchEvent(new Event('pause'))
    }
    class SilentContext {
      state = 'running'
      resume() {
        return Promise.resolve()
      }
      close() {
        this.state = 'closed'
        return Promise.resolve()
      }
    }
    Object.defineProperty(window, 'AudioContext', { value: SilentContext })
  })
  await page.goto('/')
  await page.evaluate(() => {
    const el = document.createElement('div')
    el.id = 'fixture'
    document.body.append(el)
  })
  // Test-only composition of production components; no production route or real media access.
  await page.addScriptTag({ type: 'module', url: '/src/test/browser/listening-coordination.tsx' })
  await page.getByRole('button', { name: 'Play clip', exact: true }).click()
  await expect(page.getByText('Playing clip.', { exact: true })).toBeVisible()
  await page.locator('audio').evaluate((el: HTMLAudioElement) => {
    el.currentTime = 5
    el.dispatchEvent(new Event('timeupdate'))
  })
  await page.getByRole('button', { name: 'Listen to fixture' }).click()
  await expect(page.getByText(/Clip paused because another reading started/)).toBeVisible()
  expect(await page.locator('audio').evaluate((el: HTMLAudioElement) => el.currentTime)).toBe(5)
  await page.getByRole('group', { name: 'Playback' }).getByRole('button', { name: 'Resume clip' }).click()
  await expect(page.getByText('Audio stopped because a listening clip started.')).toBeVisible()
  expect(await page.locator('audio').evaluate((el: HTMLAudioElement) => el.currentTime)).toBe(5)
  const shared = page.locator('#fixture header details')
  await shared.locator('summary').click()
  await shared.getByRole('button', { name: 'Pause clip' }).click()
  await shared.getByRole('button', { name: 'Resume clip' }).click()
  await shared.getByRole('button', { name: 'Stop clip' }).click()
  await expect(page.getByText('Clip stopped. Resume clip keeps your position.')).toBeVisible()
})
